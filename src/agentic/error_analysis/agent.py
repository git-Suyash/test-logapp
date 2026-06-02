"""Error analysis agent — multi-turn ADK agent backed by Loki tools.

The ADK InMemoryRunner handles the entire tool-call loop automatically:
it keeps dispatching tool responses back to Gemini until the model produces
a final text event, so no manual multi-turn loop is needed here.

Usage (CLI):
    from agentic.error_analysis.agent import analyze
    report = analyze(hours=1)
    print(report)
"""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from agentic.error_analysis.prompts import SYSTEM_INSTRUCTION
from agentic.runner import create_runner, run_and_get_response
from agentic.tools.loki_tools import get_error_summary, list_services, query_loki_errors
from observability.logging_config import setup_logger

load_dotenv()
logger = setup_logger()


def build_agent(model: str = "gemini-2.5-flash-lite") -> Agent:
    """Return a configured ADK Agent with all Loki tools wired in."""
    return Agent(
        name="error_analysis_agent",
        model=model,
        instruction=SYSTEM_INSTRUCTION,
        tools=[list_services, get_error_summary, query_loki_errors],
    )


def analyze(hours: int = 1, model: str = "gemini-2.5-flash-lite") -> str:
    """Run the error analysis agent and return a Markdown report.

    Args:
        hours: How far back to look for errors (passed in the user prompt).
        model: Gemini model ID to use.

    Returns:
        The agent's final Markdown report as a string.

    Raises:
        EnvironmentError: If GOOGLE_API_KEY is not set.
    """
    if not os.environ.get("GOOGLE_API_KEY"):
        raise EnvironmentError(
            "GOOGLE_API_KEY is not set. Add it to your .env file."
        )

    agent = build_agent(model=model)
    runner = create_runner(agent)

    prompt = (
        f"Analyze errors across all services in the past {hours} hour(s). "
        "Identify the top offenders, diagnose root causes from the logs, "
        "and provide actionable mitigation steps."
    )

    logger.info("ErrorAnalysisAgent starting (hours=%d, model=%s)", hours, model)
    report = run_and_get_response(runner, prompt)
    logger.info("ErrorAnalysisAgent finished")
    return report
