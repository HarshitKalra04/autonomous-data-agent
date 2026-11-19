"""Command-line entry point."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from agent.loop import run_agent


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description="Autonomous data analyst agent")
    p.add_argument("--data", required=True, help="Path to a CSV file")
    p.add_argument("--goal", required=True, help="What you want the agent to find out, in plain English")
    p.add_argument("--max-steps", type=int, default=15)
    p.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-4o-mini"))
    p.add_argument("--out", default="outputs")
    a = p.parse_args()

    data = Path(a.data)
    if not data.exists():
        raise SystemExit(f"File not found: {data}")
    run_agent(a.goal, data, Path(a.out), a.model, a.max_steps)


if __name__ == "__main__":
    main()
