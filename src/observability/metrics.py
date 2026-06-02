from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import start_http_server


PROCESSED_LOGS = Counter(
    "processed_logs_total",
    "Total processed logs"
)

PARSE_FAILURES = Counter(
    "parse_failures_total",
    "Total parse failures"
)

UNKNOWN_LOGS = Counter(
    "unknown_logs_total",
    "Total unknown logs"
)

AGENTIC_PARSED = Counter(
    "agentic_parsed_total",
    "Logs successfully parsed by the agentic (LLM) parser"
)

QUEUE_SIZE = Gauge(
    "raw_queue_size",
    "Current raw queue size"
)

ACTIVE_WORKERS = Gauge(
    "active_workers",
    "Number of active parser workers"
)

BATCH_SIZE = Gauge(
    "current_batch_size",
    "Current batch size"
)

LOKI_PUSH_FAILURES = Counter(
    "loki_push_failures_total",
    "Total Loki push failures"
)

PROCESSING_TIME = Histogram(
    "log_processing_seconds",
    "Time spent processing logs"
)

LOKI_PUSH_DURATION = Histogram(
    "loki_push_duration_seconds",
    "Loki push latency"
)

SCANNER_READ_TIME = Histogram(
    "scanner_read_seconds",
    "Scanner read latency"
)


def start_metrics_server():

    start_http_server(8000)