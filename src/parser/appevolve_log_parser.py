from datetime import datetime

from models.log_event import LogEvent

from .base_log_parser import BaseLogParser


class AppEvolveLogParser(BaseLogParser):

    def parse(self, raw_line, parsed_data):

        lines = raw_line.splitlines()

        trace = ""

        if len(lines) > 1:

            trace = "\n".join(lines[1:]).strip()

        return LogEvent(

            timestamp=datetime.strptime(
                parsed_data["timestamp"],
                "%Y-%m-%d %H:%M:%S,%f"
            ),

            log_level=parsed_data["level"].strip(),

            log_type="APPEVOLVE",

            service_name="neurostack",

            environment="production",

            message=parsed_data["message"].strip(),

            trace=trace,

            metadata={
                "pid": parsed_data["pid"],
                "logger": parsed_data["logger"].strip(),
                "source": parsed_data["source"].strip()
            },

            raw=raw_line
        )