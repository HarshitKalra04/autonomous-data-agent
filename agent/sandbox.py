"""Runs LLM-written Python in a separate process with a timeout.

This is process isolation, not a hardened security sandbox. See README.
"""
import subprocess
import sys
from pathlib import Path
from typing import Optional

MAX_OUTPUT_CHARS = 4000


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Keep the start and end of long output so the LLM sees both."""
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n...[output truncated]...\n" + text[-half:]


def run_code(code: str, data_path: Optional[Path], run_dir: Path, step: int, timeout: int = 180) -> str:
    """Execute `code` and return a text observation for the LLM."""
    charts_dir = run_dir / "charts"
    scripts_dir = run_dir / "scripts"
    data_dir = run_dir / "data"
    for d in (charts_dir, scripts_dir, data_dir):
        d.mkdir(exist_ok=True)

    # Variables the LLM's code can rely on.
    preamble = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        f"DATA_PATH = {str(data_path) if data_path else None!r}\n"
        f"DATA_DIR = {str(data_dir)!r}\n"
        f"OUTPUT_DIR = {str(run_dir)!r}\n"
        f"CHARTS_DIR = {str(charts_dir)!r}\n"
    )
    script = scripts_dir / f"step_{step:02d}.py"
    script.write_text(preamble + code, encoding="utf-8")

    before = set(p.name for p in charts_dir.iterdir())
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=run_dir,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: code exceeded the {timeout}s time limit and was stopped. Make it faster or simpler."

    after = set(p.name for p in charts_dir.iterdir())
    new_charts = sorted(after - before)

    parts = [f"exit code: {proc.returncode}"]
    if proc.stdout.strip():
        parts.append("STDOUT:\n" + _truncate(proc.stdout.strip()))
    if proc.stderr.strip():
        parts.append("STDERR:\n" + _truncate(proc.stderr.strip()))
    if new_charts:
        parts.append("New chart files saved: " + ", ".join(f"charts/{c}" for c in new_charts))
    if not proc.stdout.strip() and not proc.stderr.strip():
        parts.append("(no output - use print() to see results)")
    return "\n".join(parts)
