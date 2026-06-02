# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

LogApp is a Python-based intelligent log processing pipeline. It ingests log files from a directory, parses them by type (JSON, NGINX, AppEvolve, or unknown), and ships them to Grafana Loki. It also exports Prometheus metrics and OpenTelemetry traces to Grafana Tempo. The full observability stack (Loki, Grafana, Prometheus, Tempo, Alloy) runs via Docker Compose.

## Running the Project

```bash
# Set up Python environment
uv init
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac
uv sync

# Start the observability stack (Docker required)
docker compose up -d

# Run the app
uv run src/main.py
```

**Service URLs:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Loki: http://localhost:3100
- Tempo: http://localhost:3200
- App metrics: http://localhost:8000

There are no test or lint configurations in the project.

## Architecture

**Data flow:**

```
data/logs/  →  DirectoryReader  →  raw_queue  →  4x ParserWorker threads
                (SQLite checkpoint)                    ↓
                                              LogTypeChecker (regex)
                                                    ↓
                                             ParserFactory → parser
                                                    ↓
                                             BatchProcessor (100 logs or 5s)
                                                    ↓
                                              LokiSink → Loki HTTP API
```

Failed/unparseable logs go to `data/dead_letter/` (JSON files).

**Key source files:**

| File | Role |
|------|------|
| `src/main.py` | Entry point: starts metrics server, spawns workers, starts directory scan |
| `src/ingestion/scanners/directory_scanner.py` | Recursively scans `data/logs/`, handles multi-line log aggregation |
| `src/ingestion/checkpoint/state_manager.py` | SQLite-backed file offset tracking (inode + byte offset) for resumable reads |
| `src/ingestion/log_type_checker.py` | Regex pattern matching to classify logs as JSON, NGINX, APPEVOLVE, or UNKNOWN |
| `src/parser/parser_factory.py` | Routes classified logs to the correct parser |
| `src/pipeline/parser_worker.py` | Thread pool (4 daemon threads) that dequeues raw logs, parses, and batches |
| `src/pipeline/batch_processor.py` | Accumulates parsed `LogEvent`s and flushes to Loki every 100 events or 5 seconds |
| `src/storage/loki_sink.py` | HTTP client that pushes batches to Loki with structured labels |
| `src/models/log_event.py` | `LogEvent` dataclass — the canonical schema passed between all components |
| `src/observability/metrics.py` | Prometheus counters/gauges (processed_logs_total, parse_failures, queue_size, etc.) |
| `src/observability/tracing.py` | OpenTelemetry TracerProvider exporting to Tempo via OTLP (localhost:4317) |
| `src/pipeline/queues.py` | Shared `raw_queue` (maxsize 50,000) used across ingestion and workers |

**Parsers** (`src/parser/`): `JsonLogParser`, `NginxLogParser`, `AppEvolveLogParser` are active. `AgenticLogParser` is a stub for future AI-powered parsing via Google ADK (`src/agentic/` is empty).

**Infrastructure configs:** `alloy/config.alloy`, `loki/local-config.yaml`, `prometheus/prometheus.yml`, `tempo/tempo.yml` configure the Docker-based stack. Alloy uses `host.docker.internal` to reach the host app.

**Runtime directories** (created at startup, gitignored):
- `runtime_logs/logapp.log` — rotating application log (10MB max)
- `data/checkpoints/scanner_state.db` — SQLite checkpoint state
- `data/dead_letter/` — unparseable logs as JSON files
- `data/logs/` — input directory; drop log files here for processing
