from datetime import datetime

from models.log_event import LogEvent
from .base_log_parser import BaseLogParser


_TIMESTAMP_FIELDS = [
    "timestamp", "time", "@timestamp", "datetime",
    "date", "ts", "logged_at", "created_at", "event_time",
]

_TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
]


def _parse_timestamp(data: dict) -> datetime:
    for field in _TIMESTAMP_FIELDS:
        raw = data.get(field)
        if not raw:
            continue
        if isinstance(raw, (int, float)):
            # Unix seconds or milliseconds
            ts = raw / 1000 if raw > 1e10 else raw
            return datetime.utcfromtimestamp(ts)
        raw_str = str(raw)
        for fmt in _TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(raw_str, fmt)
                # Strip tz so all datetimes are naive UTC
                return dt.replace(tzinfo=None)
            except ValueError:
                continue
    return datetime.utcnow()


class JsonLogParser(BaseLogParser):

    def parse(self, raw_line, parsed_data):

        return LogEvent(
            timestamp=_parse_timestamp(parsed_data),
            log_level=parsed_data.get("log_level", "INFO"),
            log_type="JSON",
            service_name=parsed_data.get("service_name", "unknown"),
            environment=parsed_data.get("environment", "unknown"),
            message=parsed_data.get("message", ""),
            metadata=parsed_data,
            raw=raw_line,
        )
