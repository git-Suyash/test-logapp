import threading
import time

from opentelemetry import trace as otel_trace

from ingestion.log_type_checker import LogTypeChecker

from parser.parser_factory import ParserFactory

from pipeline.queues import raw_queue

from pipeline.batch_processor import BatchProcessor

from observability.logging_config import setup_logger

from pipeline.dead_letter_handler import DeadLetterHandler

from observability.metrics import (
    PROCESSED_LOGS,
    PARSE_FAILURES,
    UNKNOWN_LOGS,
    AGENTIC_PARSED,
    ACTIVE_WORKERS,
    PROCESSING_TIME,
)

from observability.tracing import tracer


logger = setup_logger()


class ParserWorker:

    def __init__(self, worker_count=4):

        self.batch_processor = BatchProcessor()

        self.worker_count = worker_count

        self.dlq = DeadLetterHandler()

    def drain(self):
        raw_queue.join()
        self.batch_processor.flush()

    def start(self):

        logger.info(
            f"Starting {self.worker_count} parser workers"
        )

        for index in range(self.worker_count):

            thread = threading.Thread(
                target=self._worker_loop,
                name=f"parser-worker-{index}"
            )

            thread.daemon = True

            thread.start()

    def _worker_loop(self):

        ACTIVE_WORKERS.inc()

        while True:

            raw_line = raw_queue.get()

            start = time.time()

            log_type = "UNKNOWN"

            with tracer.start_as_current_span("parse_log"):

                try:

                    log_type, parsed_data = (
                        LogTypeChecker.check_log_type(raw_line)
                    )

                    if log_type == "UNKNOWN":
                        UNKNOWN_LOGS.inc()
                        logger.info(
                            "Unknown log type — attempting agentic parsing"
                        )

                    parser = ParserFactory.get_parser(log_type)

                    event = parser.parse(raw_line, parsed_data)

                    span_ctx = otel_trace.get_current_span().get_span_context()
                    if span_ctx.is_valid:
                        event.trace = format(span_ctx.trace_id, "032x")

                    self.batch_processor.add(event)

                    if log_type == "UNKNOWN":
                        AGENTIC_PARSED.inc()

                    PROCESSED_LOGS.inc()

                except Exception as e:

                    PARSE_FAILURES.inc()

                    reason = (
                        "unknown_log_type"
                        if log_type == "UNKNOWN"
                        else "parser_exception"
                    )

                    self.dlq.write(
                        raw_log=raw_line,
                        reason=reason,
                        error=str(e)
                    )

                    logger.exception(
                        f"Parsing failed: {e}"
                    )

                finally:

                    PROCESSING_TIME.observe(
                        time.time() - start
                    )

            raw_queue.task_done()