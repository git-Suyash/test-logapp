import signal
import sys
import time

from ingestion.scanners.directory_scanner import DirectoryReader
from ingestion.http_ingestion import start_http_ingestion

from pipeline.parser_worker import ParserWorker

from observability.metrics import start_metrics_server

from observability.logging_config import setup_logger


logger = setup_logger()

SCAN_INTERVAL_SECONDS = 30


def main():

    logger.info("Starting logApp")

    start_metrics_server()

    start_http_ingestion(port=8001)

    worker = ParserWorker(worker_count=4)
    worker.start()

    scanner = DirectoryReader()

    def _shutdown(sig, frame):
        logger.info("Shutdown signal received — draining queue and exiting")
        worker.drain()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info(
        "LogApp running — scanning every %ds. Press Ctrl+C to stop.",
        SCAN_INTERVAL_SECONDS,
    )

    while True:
        scanner.scan_for_data()
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()