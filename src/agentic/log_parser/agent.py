"""Log parser agent — stateless single-shot ADK agent.

Wraps the LogParserAgent in the google-adk Agent/InMemoryRunner pattern.
Each parse() call gets its own session UUID so concurrent worker threads
never share state.  Rate limiting is enforced at the class level (4 RPM)
to stay within the free-tier Gemini quota.
"""

import json
import os
import threading
import time

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.genai import types

from agentic.log_parser.prompts import SYSTEM_INSTRUCTION
from agentic.runner import create_runner, run_and_get_response
from observability.logging_config import setup_logger

load_dotenv()
logger = setup_logger()


class _RateLimiter:
    """Sliding-window token bucket. Thread-safe across all worker threads."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._lock = threading.Lock()
        self._max = max_calls
        self._window = window_seconds
        self._call_times: list[float] = []

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._call_times = [t for t in self._call_times if now - t < self._window]
                if len(self._call_times) < self._max:
                    self._call_times.append(now)
                    return
                wait = self._window - (now - self._call_times[0]) + 0.1
            time.sleep(wait)


# 4 RPM — stays safely below the 5 RPM free-tier cap on gemini-2.5-flash-lite
_rate_limiter = _RateLimiter(max_calls=4, window_seconds=60.0)


def build_agent(model: str = "gemini-2.5-flash-lite") -> Agent:
    """Return a configured ADK Agent for single-shot log parsing."""
    return Agent(
        name="log_parser_agent",
        model=model,
        instruction=SYSTEM_INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )


class LogParserAgent:
    """Thread-safe ADK-backed log parser. One instance per process."""

    def __init__(self, model: str = "gemini-2.5-flash-lite") -> None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GOOGLE_API_KEY is not set. "
                "Get a free key at https://ai.google.dev/gemini-api/docs/api-key "
                "and add it to a .env file at the project root."
            )
        self._agent = build_agent(model=model)
        self._runner = create_runner(self._agent)
        logger.info("LogParserAgent initialised (model=%s)", model)

    def parse(self, raw_log: str) -> dict:
        """Rate-limit, call the ADK agent, and return a structured dict."""
        _rate_limiter.acquire()

        text = run_and_get_response(self._runner, raw_log[:3000])

        # Strip markdown fences the model occasionally emits despite the mime type
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1].lstrip("json").strip() if len(parts) > 1 else text

        parsed = json.loads(text)
        # Guard: take first element if model returns a list
        if isinstance(parsed, list):
            parsed = parsed[0] if parsed else {}
        return parsed


def _init_agent() -> "LogParserAgent | None":
    try:
        return LogParserAgent()
    except EnvironmentError as exc:
        logger.warning("Agentic parser disabled — %s", exc)
        return None


# Module-level singleton shared across all ParserWorker threads
log_parser_agent: LogParserAgent | None = _init_agent()
