"""Command-line entry point."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from agent.loop import run_agent


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description="Autonomous analyst agent")
    p.add_argument("--goal", required=True, help="What you want the agent to achieve, in plain English")
    p.add_argument("--data", default=None, help="Optional CSV file. Without it the agent sources data live from public APIs")
    p.add_argument("--inject-failure", choices=["fetch", "code"], default=None,
                   help="Test mode: make the first fetch_url or run_python call fail on purpose")
    p.add_argument("--max-steps", type=int, default=15)
    p.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-4o-mini"))
    p.add_argument("--step-delay", type=float, default=float(os.getenv("STEP_DELAY", "4")),
                   help="Seconds to wait between LLM calls (helps with free-tier rate limits)")
    p.add_argument("--out", default="outputs")
    a = p.parse_args()

    data = None
    if a.data:
        data = Path(a.data)
        if not data.exists():
            raise SystemExit(f"File not found: {data}")
    run_agent(a.goal, data, Path(a.out), a.model, a.max_steps, inject_failure=a.inject_failure, step_delay=a.step_delay)


if __name__ == "__main__":
    main()
