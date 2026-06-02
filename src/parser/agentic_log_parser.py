from datetime import datetime, timedelta

from models.log_event import LogEvent
from .base_log_parser import BaseLogParser
from agentic.log_parser.agent import log_parser_agent


_TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
]

# Loki rejects samples older than reject_old_samples_max_age (365d).
# If the model guesses a wrong year we fall back to now().
_MAX_AGE = timedelta(days=350)


def _parse_timestamp(ts_str: str) -> datetime:
    now = datetime.utcnow()
    for fmt in _TIMESTAMP_FORMATS:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt < now - _MAX_AGE or dt > now + timedelta(days=1):
                return now
            return dt
        except ValueError:
            continue
    return now


class AgenticLogParser(BaseLogParser):

    def parse(self, raw_line, parsed_data):

        if log_parser_agent is None:
            raise RuntimeError(
                "Agentic parser is unavailable: GOOGLE_API_KEY is not set"
            )

        result = log_parser_agent.parse(raw_line)

        ts_str = result.get("timestamp_str", "").strip()
        timestamp = _parse_timestamp(ts_str) if ts_str else datetime.utcnow()

        return LogEvent(
            timestamp=timestamp,
            log_level=result.get("log_level", "UNKNOWN"),
            log_type="AGENTIC",
            service_name=result.get("service_name", "unknown"),
            environment=result.get("environment", "unknown"),
            message=result.get("message", raw_line[:500]),
            metadata=result.get("metadata", {}),
            raw=raw_line,
        )
