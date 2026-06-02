import json
import time
from dataclasses import asdict

import requests

from observability.logging_config import setup_logger

from observability.metrics import (
    LOKI_PUSH_FAILURES,
    LOKI_PUSH_DURATION
)

from observability.tracing import tracer


logger = setup_logger()


class LokiSink:

    def __init__(self):

        self.url = (
            "http://localhost:3100/loki/api/v1/push"
        )

    def push(self, events):

        with tracer.start_as_current_span(
            "push_loki"
        ):

            start = time.time()

            try:

                streams = []

                for event in events:

                    streams.append(
                        {
                            "stream": {
                                "service": event.service_name,
                                "level": event.log_level,
                                "environment": event.environment,
                                "type": event.log_type,
                                "date": event.timestamp.strftime("%Y-%m-%d")
                            },
                            "values": [
                                [
                                    str(
                                        int(
                                            event.timestamp.timestamp()
                                            * 1e9
                                        )
                                    ),
                                    json.dumps(
                                        asdict(event),
                                        default=str
                                    )
                                ]
                            ]
                        }
                    )

                payload = {
                    "streams": streams
                }

                response = requests.post(
                    self.url,
                    json=payload
                )

                response.raise_for_status()

                logger.info(
                    f"Pushed {len(events)} logs to Loki"
                )

            except requests.exceptions.HTTPError as e:

                LOKI_PUSH_FAILURES.inc()

                body = e.response.text[:500] if e.response is not None else ""
                logger.exception(
                    f"Loki push failed: {e} | body: {body}"
                )

            except Exception as e:

                LOKI_PUSH_FAILURES.inc()

                logger.exception(
                    f"Loki push failed: {e}"
                )

            finally:

                LOKI_PUSH_DURATION.observe(
                    time.time() - start
                )