from abc import ABC, abstractmethod

from models.log_event import LogEvent


class BaseLogParser(ABC):

    @abstractmethod
    def parse(self, raw_line: str, parsed_data: dict) -> LogEvent:
        pass
