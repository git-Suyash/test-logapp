"""Shared ADK runner utilities for all LogApp agents.

Each agent module calls create_runner() to get an InMemoryRunner bound to its
Agent instance, then calls run_and_get_response() to drive a single request
through the full agentic loop (tool calls handled automatically by ADK).
"""

import uuid

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


def create_runner(agent: Agent, app_name: str = "logapp") -> Runner:
    """Return a Runner wired to *agent* with in-memory session storage.

    Uses Runner (not InMemoryRunner) so we can set auto_create_session=True,
    which creates a new session on the fly when run() sees an unknown
    session_id.  This avoids an explicit async create_session() call before
    each request.
    """
    return Runner(
        agent=agent,
        app_name=app_name,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )


_APP_NAME = "logapp"
_USER_ID = "logapp"


def run_and_get_response(
    runner: Runner,
    prompt: str,
    session_id: str | None = None,
) -> str:
    """Drive *runner* with a single user message and return the final text.

    ADK handles the full tool-call loop internally: the runner keeps calling
    the model and dispatching tool responses until it produces a final text
    event.  Each call gets a fresh session so state never leaks between calls.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    for event in runner.run(
        user_id=_USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    return part.text

    return "(no response)"
