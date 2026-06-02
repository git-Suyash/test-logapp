from abc import ABC, abstractmethod

class BaseScanner(ABC):

    def __init__(self):
        pass


    @abstractmethod
    def scan_for_data(self):
        pass
