from datetime import datetime

from models.log_event import LogEvent, HttpInfo
from .base_log_parser import BaseLogParser


class NginxLogParser(BaseLogParser):

    def parse(self, raw_line, parsed_data):

        return LogEvent(
            timestamp=datetime.utcnow(),
            log_level="INFO",
            log_type="NGINX",
            service_name="nginx",
            environment="production",
            message=f"{parsed_data['method']} {parsed_data['request']}",
            http=HttpInfo(
                status=int(parsed_data["status"]),
                path=parsed_data["request"]
            ),
            metadata=parsed_data,
            raw=raw_line
        )


# {
#   "timestamp": "2026-04-02T23:03:28.550Z",
#   "log_level": "INFO",
#   "log_type": "APPEVOLVE",
#   "service_name": "neurostack",
#   "environment": "production",
#   "message": "Logging initialized (CONSOLIDATED MODE)",
#   "http": {
#     "status": null,
#     "path": null,
#     "duration_ms": null
#   },
#   "metadata": {
#     "pid": "22880",
#     "logger": "root",
#     "source": "config.py:144",
#     "day_dir": "C:\\Users\\...\\logs\\2026-04-02",
#     "all_logs_file": "consolidated-backend.log"
#   }
# }