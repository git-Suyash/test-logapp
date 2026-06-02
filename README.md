# LogApp — Intelligent Log Processing & Observability Platform

## Overview

LogApp is a production-grade intelligent log processing and observability platform built using:

* Python
* Grafana Alloy
* Loki
* Grafana
* Prometheus
* OpenTelemetry
* Tempo

The system can:

* Process structured and unstructured logs
* Detect log types
* Normalize logs into a unified schema
* Push logs to Loki
* Provide centralized observability
* Monitor metrics and traces
* Support future AI-powered parsing using Google ADK

---

# Features

## Log Processing

* Recursive directory scanning
* Stateful checkpointing
* Multi-threaded parsing workers
* Batch processing
* Loki ingestion
* Dead letter queue support

---

## Observability

### Logs

* Runtime application logs
* Pipeline logs
* Parsing logs
* Loki ingestion logs

### Metrics

* Processed logs/sec
* Queue size
* Parsing failures
* Loki push latency
* Worker utilization

### Traces

* File scanning latency
* Parsing latency
* Loki push latency
* Batch flush tracing

---

# Tech Stack

| Component     | Purpose                     |
| ------------- | --------------------------- |
| Grafana       | Visualization               |
| Loki          | Log storage                 |
| Prometheus    | Metrics                     |
| Tempo         | Distributed tracing         |
| Alloy         | Unified telemetry collector |
| OpenTelemetry | Tracing                     |
| Python        | Processing engine           |

---

# Project Structure

```text
logApp/
│
├── docker-compose.yml
├── requirements.txt
├── README.md
├── .gitignore
│
├── alloy/
├── loki/
├── prometheus/
├── tempo/
│
├── runtime_logs/
├── data/
│
└── src/
```

---

# Setup Instructions

## 1. Clone Repository

```bash
git clone <repo_url>
cd logApp
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux / Mac

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Start Observability Stack

```bash
docker compose up -d
```

---

## 5. Start Application

```bash
python src/main.py
```

---

# Grafana Access

URL:

```text
http://localhost:3000
```

Default credentials:

```text
admin
admin
```

---

# Data Sources

## Loki

```text
http://loki:3100
```

## Prometheus

```text
http://prometheus:9090
```

## Tempo

```text
http://tempo:3200
```

---

# Example Queries

## Loki

```logql
{service="logApp"}
```

---

## Prometheus

```promql
processed_logs_total
```

---

# Future Scope

* AI-powered unknown log parsing
* Google ADK integration
* Dynamic parser generation
* Real-time anomaly detection
* Alerting system
* Kafka integration
* Distributed ingestion architecture
* Kubernetes deployment
* Multi-tenant observability

---

# Architecture

```text
External Logs
     ↓
Log Processing Pipeline
     ↓
Loki
     ↓
Grafana

Metrics → Prometheus → Grafana

Traces → Alloy → Tempo → Grafana
```

---

# License

MIT
