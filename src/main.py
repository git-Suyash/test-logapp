from ingestion.scanners.directory_scanner import DirectoryReader
from ingestion.http_ingestion import start_http_ingestion

from pipeline.parser_worker import ParserWorker

from observability.metrics import start_metrics_server

from observability.logging_config import setup_logger


logger = setup_logger()


def main():

    logger.info("Starting logApp")

    start_metrics_server()

    start_http_ingestion(port=8001)

    worker = ParserWorker(worker_count=4)

    worker.start()

    scanner = DirectoryReader()

    scanner.scan_for_data()

    worker.drain()


if __name__ == "__main__":
    main()