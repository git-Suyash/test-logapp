import threading
import time

from storage.loki_sink import LokiSink
from observability.logging_config import setup_logger

logger = setup_logger()


class BatchProcessor:

    def __init__(self):
        self.lock = threading.Lock()

        self.batch = []
        self.batch_size = 100
        self.flush_interval = 5

        self.sink = LokiSink()

        threading.Thread(
            target=self._flush_loop,
            daemon=True
        ).start()

    def add(self, event):

        should_flush = False

        with self.lock:
            self.batch.append(event)

            if len(self.batch) >= self.batch_size:
                should_flush = True

        if should_flush:
            self.flush()

    def flush(self):

        with self.lock:

            if not self.batch:
                return

            events_to_send = self.batch.copy()
            self.batch.clear()

        try:

            self.sink.push(events_to_send)

            logger.info(
                f"Flushed {len(events_to_send)} logs to Loki"
            )

        except Exception as e:

            logger.exception(
                f"Loki push failed: {e}"
            )

            # put logs back so they aren't lost
            with self.lock:
                self.batch = events_to_send + self.batch

            raise

    def _flush_loop(self):

        while True:

            time.sleep(self.flush_interval)

            self.flush()