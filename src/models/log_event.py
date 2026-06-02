from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class HttpInfo:
    status: int | None = None
    path: str | None = None
    duration_ms: float | None = None


@dataclass
class LogEvent:

    timestamp: datetime | None

    log_level: str

    log_type: str

    service_name: str

    environment: str

    message: str

    # NEW
    trace: str = ""

    http: HttpInfo = field(default_factory=HttpInfo)

    metadata: dict[str, Any] = field(default_factory=dict)

    raw: str = ""