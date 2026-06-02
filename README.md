# LogApp — Intelligent Log Processing & Observability Platform

LogApp is a production-grade log processing pipeline with a full observability stack and AI-powered analysis. It ingests logs from a directory or over HTTP, classifies and parses them, ships them to Grafana Loki with OpenTelemetry trace IDs attached, and exposes Prometheus metrics. A Google ADK agent can query Loki and produce structured root-cause reports on demand.

---

## Architecture

```
                         ┌─────────────────────────────────────────┐
                         │              Ingestion Layer             │
                         │                                          │
  data/logs/  ──────▶  DirectoryReader                             │
                         │  (SQLite checkpoint, multi-line merge)   │
  HTTP POST   ──────▶  FastAPI /ingest (port 8001)                 │
                         └──────────────┬──────────────────────────┘
                                        │
                                   raw_queue
                                (maxsize 50 000)
                                        │
                         ┌──────────────▼──────────────────────────┐
                         │           4× ParserWorker threads        │
                         │                                          │
                         │  LogTypeChecker ──▶ ParserFactory        │
                         │       │                   │              │
                         │  JSON │ NGINX │ APPEVOLVE │ AGENTIC      │
                         │  parser  parser   parser    (ADK/Gemini) │
                         │                                          │
                         │  OTel trace ID injected into LogEvent    │
                         └──────────────┬──────────────────────────┘
                                        │
                              BatchProcessor (100 logs / 5 s)
                                        │
                                    LokiSink
                                        │
                    ┌───────────────────▼──────────────────────────┐
                    │                Grafana Stack                  │
                    │                                              │
                    │   Loki ◀── Alloy ◀── runtime_logs/          │
                    │   Prometheus ◀── app metrics (port 8000)     │
                    │   Tempo ◀── OTLP traces (port 4317)          │
                    │   Grafana (port 3000) ── 3 pre-built boards  │
                    └──────────────────────────────────────────────┘

Failed / unparseable logs ──▶ data/dead_letter/  (JSON files)
```

---

## Features

### Log Ingestion

| Method | Details |
|---|---|
| Directory scan | Recursively watches `data/logs/`; SQLite checkpoint tracks inode + byte offset for resumable reads |
| HTTP endpoint | `POST /ingest` on port 8001; accepts `text/plain`, `{"log": "..."}`, or `{"logs": [...]}` |
| Multi-line merge | Continuation lines (stack traces, JSON blobs) are aggregated before queuing |

### Log Parsing

| Type | Detected by | Parser |
|---|---|---|
| JSON | `{` prefix or `"level"` key | `JsonLogParser` |
| NGINX | `combined` access-log pattern | `NginxLogParser` |
| AppEvolve | AppEvolve-specific field pattern | `AppEvolveLogParser` |
| AGENTIC | Anything else | `AgenticLogParser` → Gemini via ADK |

Every parsed log becomes a `LogEvent` with normalised fields: `timestamp`, `log_level`, `log_type`, `service_name`, `environment`, `message`, `metadata`, `trace`, `raw`.

### OpenTelemetry Trace ID Injection

Each `parse_log` span carries a real OTel trace ID that is stamped onto the `LogEvent` and shipped to Loki as the `trace` JSON field. Grafana's Loki derived-field rule extracts it with:

```
'"trace": "([0-9a-f]{32})"'
```

…and renders a **View Trace in Tempo** link directly in the log explorer.

### Observability

- **Prometheus metrics** (port 8000): `processed_logs_total`, `parse_failures_total`, `queue_size`, `loki_push_duration_seconds`, `agentic_calls_total`
- **OTel traces** → Tempo: file scan, parse, batch flush
- **Runtime logs** → Alloy → Loki (`{source="runtime_logs"}`)

### Grafana Dashboards (auto-provisioned)

Three dashboards load automatically when the stack starts — no manual import needed.

| Dashboard | UID | Description |
|---|---|---|
| Ingested Logs | `logapp-ingested-logs` | Log volume by type/service, full log explorer with `service`, `level`, `log_type` filters |
| Pipeline Health | `logapp-pipeline-health` | Throughput, parse-failure rate, queue depth, Loki push latency, runtime log stream |
| Error Rates | `logapp-error-rates` | ERROR/CRITICAL/WARNING counts per service, colour-coded stat tiles, recent error log panel |

### AI-Powered Error Analysis (Google ADK)

A multi-turn Gemini agent queries Loki with three tools and produces a structured Markdown incident report:

```
list_services()  →  get_error_summary(hours)  →  query_loki_errors(service, …)
                                                          ↓
                                               Structured Markdown report
                                    (impacted services · root causes · mitigations)
```

The ADK Runner handles the entire tool-call loop automatically.

```bash
uv run src/analyze_errors.py              # last 1 hour
uv run src/analyze_errors.py --hours 6   # last 6 hours
uv run src/analyze_errors.py --model gemini-2.5-flash --hours 24
```

---

## Tech Stack

| Component | Version / Notes |
|---|---|
| Python | 3.13 |
| [uv](https://github.com/astral-sh/uv) | Dependency & venv management |
| FastAPI + Uvicorn | HTTP ingestion server |
| google-adk | ≥ 1.34 — Agent/Runner/InMemorySessionService |
| OpenTelemetry | SDK + OTLP/gRPC exporter |
| Prometheus client | Metrics exposition |
| Grafana | Visualisation (port 3000) |
| Loki | Log storage (port 3100) |
| Prometheus | Metrics storage (port 9090) |
| Tempo | Trace storage (port 3200) |
| Alloy | Unified telemetry collector |

---

## Project Structure

```
logApp/
├── docker-compose.yml
├── pyproject.toml               ← uv-managed dependencies
├── requirements.txt             ← pip fallback
├── .env                         ← GOOGLE_API_KEY (gitignored)
├── .env.example
│
├── alloy/config.alloy
├── loki/local-config.yaml
├── prometheus/prometheus.yml
├── tempo/tempo.yml
│
├── grafana/provisioning/
│   ├── datasources/datasources.yaml   ← Loki + Prometheus + Tempo (stable UIDs, derived fields)
│   └── dashboards/
│       ├── dashboards.yaml            ← provider config
│       ├── ingested_logs.json
│       ├── pipeline_health.json
│       └── error_rates.json
│
├── data/
│   ├── logs/                    ← drop log files here
│   ├── checkpoints/             ← SQLite scanner state (runtime, gitignored)
│   └── dead_letter/             ← unparseable logs as JSON (runtime, gitignored)
│
├── runtime_logs/                ← rotating app log (gitignored)
│
└── src/
    ├── main.py                  ← entry point
    ├── analyze_errors.py        ← error analysis CLI
    │
    ├── agentic/                 ← Google ADK agents
    │   ├── runner.py            ← shared create_runner / run_and_get_response
    │   ├── tools/
    │   │   └── loki_tools.py   ← list_services, get_error_summary, query_loki_errors
    │   ├── error_analysis/
    │   │   ├── agent.py        ← build_agent(), analyze()
    │   │   └── prompts.py      ← SRE analyst system instruction
    │   └── log_parser/
    │       ├── agent.py        ← LogParserAgent class + singleton
    │       └── prompts.py      ← JSON extraction system instruction
    │
    ├── config/settings.py
    ├── ingestion/
    │   ├── http_ingestion.py    ← FastAPI app + start_http_ingestion()
    │   ├── log_type_checker.py
    │   ├── checkpoint/state_manager.py
    │   └── scanners/directory_scanner.py
    ├── models/log_event.py
    ├── observability/
    │   ├── logging_config.py
    │   ├── metrics.py
    │   └── tracing.py
    ├── parser/
    │   ├── parser_factory.py
    │   ├── json_log_parser.py
    │   ├── nginx_log_parser.py
    │   ├── appevolve_log_parser.py
    │   └── agentic_log_parser.py
    ├── pipeline/
    │   ├── parser_worker.py     ← trace ID injection happens here
    │   ├── batch_processor.py
    │   ├── queues.py
    │   └── dead_letter_handler.py
    └── storage/loki_sink.py
```

---

## Setup

### Prerequisites

- Docker Desktop
- Python 3.13
- [uv](https://github.com/astral-sh/uv) (`pip install uv` or `brew install uv`)
- A [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key) API key (free tier is fine for the ADK agents)

### 1. Clone

```bash
git clone <repo_url>
cd logApp
```

### 2. Configure environment

```bash
cp .env.example .env
# edit .env and set GOOGLE_API_KEY=<your_key>
```

### 3. Install Python dependencies

```bash
uv sync
```

### 4. Start the observability stack

```bash
docker compose up -d
```

Grafana will auto-provision all three dashboards and the three data sources on first start. No manual configuration required.

### 5. Run the app

```bash
uv run src/main.py
```

This starts (concurrently):

- Prometheus metrics server on **:8000**
- HTTP ingestion server on **:8001**
- 4 parser worker threads
- Directory scanner over `data/logs/`

---

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Loki | http://localhost:3100 | — |
| Tempo | http://localhost:3200 | — |
| App metrics | http://localhost:8000/metrics | — |
| HTTP ingest | http://localhost:8001/ingest | — |
| Ingest docs | http://localhost:8001/docs | — |

---

## Usage

### Ingest logs via directory

Drop any log files into `data/logs/` (subdirectories are fine). The scanner picks them up within seconds.

### Ingest logs via HTTP

```bash
# Plain text — one log per line
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: text/plain" \
  --data-binary "2024-01-15T10:23:45 ERROR payment-svc timeout after 5000ms"

# Single JSON log
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{"log": "{\"level\": \"ERROR\", \"service\": \"auth\", \"message\": \"login failed\"}"}'

# Batch JSON logs
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{"logs": ["line one", "line two"]}'
```

### Run AI error analysis

```bash
# Analyze the last hour (default)
uv run src/analyze_errors.py

# Wider window with a more capable model
uv run src/analyze_errors.py --hours 24 --model gemini-2.5-flash
```

### Example Loki queries

```logql
# All ingested logs
{type=~"JSON|NGINX|APPEVOLVE|AGENTIC"}

# Errors for a specific service
{type=~"JSON|NGINX|APPEVOLVE|AGENTIC", service="payment-svc", level="ERROR"}

# LogApp's own runtime logs (shipped by Alloy)
{source="runtime_logs"}

# Error rate per service (logs/min)
sum by (service) (count_over_time({type=~"JSON|NGINX|APPEVOLVE|AGENTIC", level=~"ERROR|CRITICAL"}[1m]))
```

### Example Prometheus queries

```promql
# Ingestion throughput
rate(processed_logs_total[1m])

# Parse failure rate
rate(parse_failures_total[1m])

# Current queue depth
queue_size

# Loki push p95 latency
histogram_quantile(0.95, rate(loki_push_duration_seconds_bucket[5m]))
```

---

## Loki → Tempo Trace Linking

Every parsed log contains a `"trace"` field with the 32-hex OTel trace ID of the span that processed it. The Grafana Loki datasource is configured to extract this automatically and render a **View Trace in Tempo** button in the Explore log viewer — no manual setup needed.

The derived-field config in `grafana/provisioning/datasources/datasources.yaml`:

```yaml
derivedFields:
  - name: TraceID
    matcherRegex: '"trace": "([0-9a-f]{32})"'
    url: "${__value.raw}"
    datasourceUid: tempo
    urlDisplayLabel: "View Trace in Tempo"
```

---

## Agentic Layer (Google ADK)

### Structure

```
src/agentic/
├── runner.py                   ← create_runner() / run_and_get_response()
├── tools/
│   └── loki_tools.py           ← ADK tools: list_services, get_error_summary, query_loki_errors
├── error_analysis/
│   ├── agent.py                ← analyze(hours, model) → Markdown report
│   └── prompts.py              ← SRE analyst system instruction
└── log_parser/
    ├── agent.py                ← LogParserAgent.parse(raw_log) → dict
    └── prompts.py              ← JSON extraction system instruction
```

### How it works

Tools are plain Python functions — ADK derives the Gemini function declarations automatically from type hints and docstrings. The shared `runner.py` creates an ADK `Runner` with `auto_create_session=True` so each call gets a fresh session without boilerplate. The Runner handles the full tool-call cycle; callers just call `run_and_get_response()` and get back text.

The `LogParserAgent` uses `generate_content_config` to enforce `response_mime_type="application/json"` and `temperature=0.0` for deterministic structured output. A thread-safe sliding-window rate limiter (4 RPM) guards the free-tier quota across all 4 parser worker threads.

---

## License

MIT
