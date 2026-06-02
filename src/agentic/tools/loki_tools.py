"""Loki query tools shared across LogApp agents.

All three functions are registered as ADK tools — plain Python functions whose
type hints and docstrings are read by ADK to generate the Gemini function
declarations automatically.  Return dicts follow the ADK convention of always
including a top-level 'status' key ('ok' | 'error') so the model can detect
failures without parsing prose.
"""

import json
import os
from datetime import datetime, timezone

import requests

LOKI_URL = os.environ.get("LOKI_URL", "http://localhost:3100")


def list_services() -> dict:
    """Return all service names that have sent logs to Loki in the last 24 hours.

    Returns:
        A dict with 'status', 'services' (list of service name strings),
        and 'count' (number of services found).
    """
    try:
        resp = requests.get(
            f"{LOKI_URL}/loki/api/v1/label/service/values",
            timeout=10,
        )
        resp.raise_for_status()
        services = [v for v in resp.json().get("data", []) if v]
        return {"status": "ok", "services": services, "count": len(services)}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "services": [], "count": 0}


def get_error_summary(hours: int = 1) -> dict:
    """Return error and critical log counts per service for the last N hours.

    Args:
        hours: Look-back window in hours. Defaults to 1.

    Returns:
        A dict with 'status', 'window_hours', 'error_counts_by_service'
        (mapping service name → count, sorted descending), and 'total_errors'.
    """
    end_ns = int(datetime.now(timezone.utc).timestamp() * 1e9)
    query = (
        "sum by (service) "
        '(count_over_time({type=~"JSON|NGINX|APPEVOLVE|AGENTIC",'
        f' level=~"ERROR|CRITICAL"}}[{hours}h]))'
    )
    try:
        resp = requests.get(
            f"{LOKI_URL}/loki/api/v1/query",
            params={"query": query, "time": str(end_ns)},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json().get("data", {}).get("result", [])
        summary: dict[str, int] = {}
        for item in result:
            svc = item.get("metric", {}).get("service", "unknown")
            count = int(item.get("value", [0, "0"])[1])
            summary[svc] = count
        summary_sorted = dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))
        return {
            "status": "ok",
            "window_hours": hours,
            "error_counts_by_service": summary_sorted,
            "total_errors": sum(summary.values()),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "window_hours": hours,
            "error_counts_by_service": {},
            "total_errors": 0,
        }


def query_loki_errors(
    service: str,
    level: str = "ERROR|CRITICAL",
    hours: int = 1,
    limit: int = 20,
) -> dict:
    """Fetch recent error log lines for a specific service from Loki.

    Args:
        service: The service name to query (must match the Loki 'service' label).
        level: Log level filter regex, e.g. 'ERROR|CRITICAL'. Defaults to both.
        hours: Look-back window in hours. Defaults to 1.
        limit: Maximum number of log entries to return. Defaults to 20.

    Returns:
        A dict with 'status', 'service', 'window_hours', 'entry_count',
        and 'entries' (list of {timestamp, level, message} dicts).
    """
    end_ns = int(datetime.now(timezone.utc).timestamp() * 1e9)
    start_ns = end_ns - hours * 3600 * int(1e9)
    query = f'{{type=~"JSON|NGINX|APPEVOLVE|AGENTIC", service="{service}", level=~"{level}"}}'

    try:
        resp = requests.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={
                "query": query,
                "start": str(start_ns),
                "end": str(end_ns),
                "limit": str(limit),
                "direction": "backward",
            },
            timeout=15,
        )
        resp.raise_for_status()
        streams = resp.json().get("data", {}).get("result", [])

        entries = []
        for stream in streams:
            labels = stream.get("stream", {})
            for ts_ns, line in stream.get("values", []):
                try:
                    message = json.loads(line).get("message", line)
                except Exception:
                    message = line
                entries.append(
                    {
                        "timestamp": datetime.fromtimestamp(
                            int(ts_ns) / 1e9, tz=timezone.utc
                        ).isoformat(),
                        "level": labels.get("level", "UNKNOWN"),
                        "message": message[:2000],
                    }
                )

        entries.sort(key=lambda x: x["timestamp"], reverse=True)
        return {
            "status": "ok",
            "service": service,
            "window_hours": hours,
            "entry_count": len(entries),
            "entries": entries[:limit],
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "service": service,
            "window_hours": hours,
            "entry_count": 0,
            "entries": [],
        }
