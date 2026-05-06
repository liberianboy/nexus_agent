"""Command-line entry point for the Nexus Agent.

Examples:

    # Run the data-center / water demo (mock mode unless API keys present)
    python -m src.cli --scenario data_center_water

    # Run the grid cyberattack demo with the heat map
    python -m src.cli --scenario grid_cyberattack --heatmap

    # Ask a custom question with human-in-the-loop tool review
    HUMAN_IN_THE_LOOP=1 python -m src.cli --question "How does drought hit grid reliability?"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .agent import is_mock_mode, run_agent, trace_agent
from .persona import SCENARIO_PRESETS

REPORTS = Path(__file__).resolve().parent.parent / "reports"


def _print_banner() -> None:
    mode = "MOCK (no API keys)" if is_mock_mode() else "LIVE (OpenAI + Tavily)"
    bar = "=" * 60
    print(bar)
    print(" Nexus Agent - Energy/Water/Food + Grid Resilience")
    print(f" Mode: {mode}")
    print(bar)


def _resolve_question(args: argparse.Namespace) -> tuple[str, str]:
    if args.question:
        return ("custom", args.question)
    if args.scenario in SCENARIO_PRESETS:
        return (args.scenario, SCENARIO_PRESETS[args.scenario]["question"])
    print(f"ERROR: unknown scenario '{args.scenario}'. "
          f"Choices: {list(SCENARIO_PRESETS)}")
    sys.exit(2)


def _save_run(scenario: str, question: str, trace: list, answer: str) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"run_{scenario}.json"
    payload = {
        "scenario": scenario,
        "question": question,
        "mode": "mock" if is_mock_mode() else "live",
        "trace": trace,
        "final_answer": answer,
    }
    out.write_text(json.dumps(payload, indent=2, default=str))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="nexus-agent")
    p.add_argument(
        "--scenario",
        choices=list(SCENARIO_PRESETS) + ["custom"],
        default="data_center_water",
    )
    p.add_argument("--question", help="custom question (overrides --scenario)")
    p.add_argument(
        "--heatmap",
        action="store_true",
        help="also render the interdependency heat map",
    )
    p.add_argument(
        "--no-trace",
        action="store_true",
        help="hide step-by-step trace, only print the final answer",
    )
    args = p.parse_args(argv)

    _print_banner()

    if args.heatmap:
        from . import heatmap

        print("\n--- Interdependency Heat Map ---")
        heatmap.main()

    scenario, question = _resolve_question(args)
    print(f"\nScenario : {scenario}")
    print(f"Question : {question}\n")

    if args.no_trace:
        answer = run_agent(question)
        trace: list = []
    else:
        trace = trace_agent(question)
        print("--- Reasoning Trace ---")
        for i, step in enumerate(trace, 1):
            tag = step["node"].upper()
            kind = step["type"]
            content = step["content"]
            tcs = step.get("tool_calls") or []
            print(f"[{i:02d}] {tag:<7} {kind:<8} {content[:140]}")
            for tc in tcs:
                print(f"        -> tool_call: {tc.get('name')}({tc.get('args')})")
        # The final synthesised answer is the last AI message in the trace
        # without tool_calls.
        answer = ""
        for step in reversed(trace):
            if step["type"] == "ai" and not step.get("tool_calls"):
                answer = step["content"]
                break

    print("\n--- Final Answer ---")
    print(answer or "(empty)")

    out = _save_run(scenario, question, trace, answer)
    print(f"\nRun saved to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
