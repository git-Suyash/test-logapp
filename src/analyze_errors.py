"""CLI entry point for the error analysis agent.

Usage:
    uv run src/analyze_errors.py            # analyze last 1 hour
    uv run src/analyze_errors.py --hours 6  # analyze last 6 hours
    uv run src/analyze_errors.py --model gemini-2.5-flash
"""

import argparse
import os
import sys

# Ensure src/ is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from agentic.error_analysis.agent import analyze


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the LogApp error analysis agent against recent Loki logs."
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=1,
        help="How many hours back to look for errors (default: 1)",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash-lite",
        help="Gemini model to use (default: gemini-2.5-flash-lite)",
    )
    args = parser.parse_args()

    print(f"\nAnalyzing errors from the last {args.hours} hour(s)...\n")
    print("=" * 70)

    report = analyze(hours=args.hours, model=args.model)

    print("\n" + "=" * 70)
    print("ERROR ANALYSIS REPORT")
    print("=" * 70 + "\n")
    print(report)
    print()


if __name__ == "__main__":
    main()
