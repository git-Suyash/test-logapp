import json
from pathlib import Path
from datetime import datetime


class DeadLetterHandler:

    def __init__(
        self,
        dlq_dir="data/dead_letter"
    ):
        self.dlq_dir = Path(dlq_dir)

        self.dlq_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def write(
        self,
        raw_log: str,
        reason: str,
        error: str | None = None
    ):

        filename = (
            f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
        )

        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "error": error,
            "raw_log": raw_log[:50000]
        }

        with open(
            self.dlq_dir / filename,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                payload,
                f,
                indent=2
            )