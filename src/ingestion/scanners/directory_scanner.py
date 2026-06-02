# from ingestion.log_type_checker import LogTypeChecker
# import os
# from collections import deque

# from .base_scanner import BaseScanner
# from .state_manager import StateManager
# from data_parser.parser_factory import ParserFactory
# from processing.log_processor import LogProcessor

# class DirectoryReader(BaseScanner):

#     def __init__(self, base_dir="data/logs", db_path="../../../temp/scanner_state.db"):
#         self.base_dir = base_dir
#         self.state_manager = StateManager(db_path)
#         self.file_queue = deque()
#         self.processor = LogProcessor()

#     def _discover_and_enqueue(self):

#         """
#         Recursively explores the data directory.
#         Sorts the subdirectories (day-wise) to keep sequential ingestion.
#         """

#         print(f" Crawling directory structure starting at: {self.base_dir}")
        
        
#         for root, dirs, files in os.walk(self.base_dir):
            
#             dirs.sort()
            
#             for file in files:
#                 full_path = os.path.join(root, file)
#                 self.file_queue.append(full_path)
                
#         print(f"Enqueued {len(self.file_queue)} files for processing.")


#     #def _send_to_next_phase(self, data_line: str):

#         """
#         Passes processed data forward to your system pipeline.
#         """
#         type, serial_data = LogTypeChecker.check_log_type(data_line)

#         if type == "EMPTY":
#             # error handling logic
#             pass
#         elif type == "JSON":
#             # to json parser
#             pass
#         elif type == "NGINX":
#             # to nginx parser
#             pass
#         elif type == "APPEVOLVE":
#             # appevolve parser
#             pass
#         elif type == "UNKNOWN":
#             # agentic parser
#             pass
        
#         # print(f"{len(data_line)}")

#     def _process_line(self,line):
#         log_type , parsed_data=LogTypeChecker.check_log_type(line)

#         parser=ParserFactory.get_parser(log_type)

#         if parser is None:
#             print("Cannot find parser for log type: ", log_type)
#             return

#         event=parser.parse(line,parsed_data)
#         self.processor.process(event)


#     def scan_for_data(self):

#         """
#         Main operational pipeline. Loops through the queue sequentially.
#         """

#         self._discover_and_enqueue()

#         while self.file_queue:
#             file_path = self.file_queue.popleft()
            
#             try:
#                 stat_info = os.stat(file_path)
#                 inode = stat_info.st_ino
#             except OSError:
#                 print(f" Skipping inaccessible file: {file_path}")
#                 continue

#             last_offset = self.state_manager.get_offset(inode)
            
#             print(f"Processing: {file_path} | Inode: {inode} | Resuming from byte: {last_offset}")

#             with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
#                 f.seek(last_offset)
                
#                 while True:
                    
#                     current_line_offset = f.tell()
#                     line = f.readline()

#                     if not line:
#                         break

                    
#                     #if not self._dummy_type_checker(line): # error here
#                         # print(f" Type validation failed at byte {current_line_offset}. Checkpoint saved.") 
#                         # Save the current line's offset so we attempt it again next runtime
#                         self.state_manager.save_state(inode, file_path, current_line_offset)
                        
#                         return 

#                     self._process_line(line)

#                 self.state_manager.save_state(inode, file_path, f.tell())
#                 print(f" Finished file: {file_path}")


# new_code
import re
import os
import time
from collections import deque

from ingestion.checkpoint.state_manager import StateManager

from pipeline.queues import raw_queue

from observability.logging_config import setup_logger

from observability.metrics import (
    QUEUE_SIZE,
    SCANNER_READ_TIME
)

from observability.tracing import tracer


logger = setup_logger()


class DirectoryReader:

    LOG_START_PATTERN = re.compile(
        r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}"
    )

    def __init__(self, base_dir="data/logs"):

        self.base_dir = base_dir

        self.state_manager = StateManager()

        self.file_queue = deque()

    def _discover_and_enqueue(self):

        logger.info(
            f"Scanning directory: {self.base_dir}"
        )

        for root, dirs, files in os.walk(self.base_dir):

            dirs.sort()

            for file in files:

                full_path = os.path.join(root, file)

                self.file_queue.append(full_path)

        logger.info(
            f"Discovered {len(self.file_queue)} files"
        )

    def scan_for_data(self):

        self._discover_and_enqueue()

        while self.file_queue:

            file_path = self.file_queue.popleft()

            with tracer.start_as_current_span("scan_file"):

                start = time.time()

                try:

                    stat_info = os.stat(file_path)

                    inode = stat_info.st_ino

                except OSError:

                    logger.exception(
                        f"Cannot access file: {file_path}"
                    )

                    continue

                last_offset = self.state_manager.get_offset(
                    inode
                )

                logger.info(
                    f"Reading {file_path} from offset {last_offset}"
                )

                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    f.seek(last_offset)

                    current_event: list[str] = []
                    # True when current_event started with a LOG_START_PATTERN
                    # line — meaning continuations (stack traces) should be
                    # appended rather than emitted as separate events.
                    event_has_timestamp = False

                    while True:

                        line = f.readline()

                        if not line:
                            break

                        if self.LOG_START_PATTERN.match(line):
                            # New timestamped event — flush whatever we have
                            if current_event:
                                raw_queue.put("".join(current_event))
                                QUEUE_SIZE.set(raw_queue.qsize())

                            current_event = [line]
                            event_has_timestamp = True

                        elif event_has_timestamp:
                            # Continuation of a multi-line event (stack trace
                            # or wrapped message after an APPEVOLVE header)
                            current_event.append(line)

                        else:
                            # Non-timestamped line (syslog, NGINX, JSON, etc.)
                            # Each such line is its own independent event.
                            if current_event:
                                raw_queue.put("".join(current_event))
                                QUEUE_SIZE.set(raw_queue.qsize())

                            current_event = [line]
                            event_has_timestamp = False

                    # push final event
                    if current_event:

                        raw_event = "".join(current_event)

                        raw_queue.put(raw_event)

                        QUEUE_SIZE.set(
                            raw_queue.qsize()
                        )

                    self.state_manager.save_state(
                        inode,
                        file_path,
                        f.tell()
                    )