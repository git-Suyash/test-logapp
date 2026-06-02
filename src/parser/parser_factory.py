from .json_log_parser import JsonLogParser
from .nginx_log_parser import NginxLogParser
from .appevolve_log_parser import AppEvolveLogParser
from .agentic_log_parser import AgenticLogParser


class ParserFactory:

    @staticmethod
    def get_parser(log_type: str):

        parsers = {
            "JSON": JsonLogParser(),
            "NGINX": NginxLogParser(),
            "APPEVOLVE": AppEvolveLogParser(),
            "UNKNOWN": AgenticLogParser()
        }

        return parsers.get(log_type,AgenticLogParser())
