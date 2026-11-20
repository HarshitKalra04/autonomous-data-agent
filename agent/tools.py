"""The tools the LLM can call, their JSON schemas, and bookkeeping for the run summary."""
import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from .sandbox import run_code
from .web import FetchError, safe_fetch

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "make_plan",
            "description": (
                "Write or revise your plan: a short numbered list of concrete steps. "
                "You MUST call this before any other tool. Call it again (with revision_reason) "
                "when a step fails or the plan no longer fits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {"type": "array", "items": {"type": "string"}, "description": "Ordered steps, each concrete and checkable."},
                    "revision_reason": {"type": "string", "description": "Only when revising: what went wrong and why the plan changes."},
                },
                "required": ["steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "HTTP GET a public URL (for example a free public API that needs no key) and save the response "
                "into DATA_DIR. Returns status, size, saved file name and a preview."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full http(s) URL including query string."},
                    "save_as": {"type": "string", "description": "Optional file name, e.g. delhi.json."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_dataset",
            "description": (
                "Profile a data file: for CSV the shape, types, missing values, statistics and sample rows; "
                "for JSON its structure. With no path it inspects the CSV provided by the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Optional name of a file saved by fetch_url."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Run Python code in a fresh process and return stdout/stderr. "
                "Predefined: DATA_PATH (CSV path or None), DATA_DIR, OUTPUT_DIR, CHARTS_DIR."
            ),
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Complete Python script to run."}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Submit the final Markdown report and end the run.",
            "parameters": {
                "type": "object",
                "properties": {"report_markdown": {"type": "string", "description": "The full final report."}},
                "required": ["report_markdown"],
            },
        },
    },
]


def is_failure(result: str) -> bool:
    """True if a tool result reports an error or a non-zero exit code."""
    if result.startswith("ERROR"):
        return True
    m = re.match(r"exit code: (-?\d+)", result)
    return bool(m and m.group(1) != "0")


def _last_line(text: str, limit: int = 200) -> str:
    """The last non-empty line of a result (for a traceback this is the actual error)."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return (lines[-1] if lines else "")[:limit]


def _shape(obj, depth: int = 0, max_depth: int = 3) -> str:
    """Short description of the structure of parsed JSON."""
    pad = "  " * depth
    if isinstance(obj, dict):
        head = f"{pad}object with {len(obj)} keys"
        if depth >= max_depth:
            return head
        lines = [head + ":"]
        for k, v in list(obj.items())[:15]:
            lines.append(f"{pad}  {k}: " + _shape(v, depth + 1, max_depth).lstrip())
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return f"{pad}empty list"
        return f"{pad}list of {len(obj)} items, first item: " + _shape(obj[0], depth + 1, max_depth).lstrip()
    return f"{pad}{type(obj).__name__} (example: {str(obj)[:40]})"


class ToolBox:
    def __init__(self, data_path: Optional[Path], run_dir: Path, inject_failure: Optional[str] = None):
        self.data_path = data_path
        self.run_dir = run_dir
        self.data_dir = run_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.plans = []            # every plan version the agent wrote
        self.last_plan_text = ""
        self.counts = {}           # tool name -> number of calls
        self.failures = 0          # tool results that reported an error
        self.failure_log = []      # one entry per failure: step, tool, error, induced
        self.current_step = 0      # set by the loop before each tool call
        self.finished = False
        self.report_path = None

        self.inject_failure = inject_failure   # None, "fetch" or "code"
        self.injected = False
        self.induced_now = False   # True only for the call that was sabotaged

        self._code_calls = 0
        self._fetch_calls = 0

    # ---- entry point -------------------------------------------------
    def call(self, name: str, args: dict) -> str:
        self.induced_now = False
        self.counts[name] = self.counts.get(name, 0) + 1
        if name != "make_plan" and not self.plans:
            result = "ERROR: no plan exists yet. Call make_plan first with your numbered steps, then continue."
        else:
            try:
                result = self._dispatch(name, args)
            except KeyError as e:
                result = f"ERROR: missing required argument {e}."
            except Exception as e:  # tool failures go back to the LLM, they never crash the run
                result = f"ERROR: {type(e).__name__}: {e}"
        if is_failure(result):
            self.failures += 1
            self.failure_log.append({
                "step": self.current_step, "tool": name,
                "error": _last_line(result), "induced": self.induced_now,
            })
        return result

    def _dispatch(self, name: str, args: dict) -> str:
        if name == "make_plan":
            return self._make_plan(args["steps"], args.get("revision_reason"))
        if name == "fetch_url":
            return self._fetch(args["url"], args.get("save_as"))
        if name == "inspect_dataset":
            return self._inspect(args.get("path"))
        if name == "run_python":
            return self._run_python(args["code"])
        if name == "finish":
            return self._finish(args["report_markdown"])
        return f"ERROR: unknown tool '{name}'."

    # ---- tools -------------------------------------------------------
    def _make_plan(self, steps, reason) -> str:
        if not isinstance(steps, list) or not steps or not all(isinstance(s, str) and s.strip() for s in steps):
            return "ERROR: 'steps' must be a non-empty list of strings."
        self.plans.append({"steps": steps, "revision_reason": reason})
        version = len(self.plans)
        title = f"PLAN v{version}" if version == 1 else f"REVISED PLAN v{version} (reason: {reason or 'not given'})"
        numbered = "\n".join(f"  {i}. {s}" for i, s in enumerate(steps, 1))
        self.last_plan_text = f"{title}\n{numbered}"
        (self.run_dir / "plan.md").write_text(
            "\n\n".join(
                (f"## Plan v{i}" + (f" (revision: {p['revision_reason']})" if p["revision_reason"] else "") + "\n"
                 + "\n".join(f"{j}. {s}" for j, s in enumerate(p["steps"], 1)))
                for i, p in enumerate(self.plans, 1)
            ),
            encoding="utf-8",
        )
        return f"Plan v{version} recorded with {len(steps)} steps. Now execute it step by step."

    def _fetch(self, url: str, save_as: Optional[str]) -> str:
        self._fetch_calls += 1
        if self.inject_failure == "fetch" and not self.injected:
            self.injected = True
            self.induced_now = True
            return "ERROR: request timed out after 15s (no response from server)."
        try:
            status, ctype, body = safe_fetch(url)
        except FetchError as e:
            return f"ERROR: {e}"
        ext = ".json" if "json" in ctype.lower() else ".csv" if "csv" in ctype.lower() else ".txt"
        clean = re.sub(r"[^A-Za-z0-9._-]", "_", Path(save_as).name) if save_as else ""
        name = clean or f"fetch_{self._fetch_calls}{ext}"
        (self.data_dir / name).write_bytes(body)
        preview = body[:1500].decode("utf-8", "replace")
        return f"HTTP {status}, content-type {ctype}, {len(body)} bytes. Saved as '{name}' (read it from DATA_DIR in run_python).\nPreview:\n{preview}"

    def _resolve(self, path: Optional[str]) -> Optional[Path]:
        if not path:
            return self.data_path
        name = Path(path).name
        candidate = self.data_dir / name
        if candidate.exists():
            return candidate
        if self.data_path and name == self.data_path.name:
            return self.data_path
        return None

    def _inspect(self, path: Optional[str]) -> str:
        target = self._resolve(path)
        if target is None:
            available = sorted(p.name for p in self.data_dir.iterdir())
            return f"ERROR: no such data file. Files available from fetch_url: {available or 'none'}. No CSV was provided by the user."
        suffix = target.suffix.lower()
        if suffix == ".csv":
            return self._inspect_csv(target)
        if suffix == ".json":
            data = json.loads(target.read_text(encoding="utf-8"))
            return "JSON structure:\n" + _shape(data)
        return "Text file, first 1500 characters:\n" + target.read_text(encoding="utf-8", errors="replace")[:1500]

    @staticmethod
    def _inspect_csv(target: Path) -> str:
        df = pd.read_csv(target)
        out = [f"Rows: {len(df)}, Columns: {df.shape[1]}", "", "Columns (dtype, missing, unique):"]
        for col in df.columns:
            out.append(f"- {col}: {df[col].dtype}, missing={int(df[col].isna().sum())}, unique={df[col].nunique()}")
        num = df.select_dtypes("number")
        if not num.empty:
            out += ["", "Numeric summary:", num.describe().round(3).T.to_string()]
        cat = df.select_dtypes(exclude="number")
        for col in cat.columns[:8]:
            out.append(f"\nTop values of {col}: {df[col].value_counts().head(5).to_dict()}")
        out += ["", "First 5 rows:", df.head(5).to_string()]
        return "\n".join(out)

    def _run_python(self, code: str) -> str:
        self._code_calls += 1
        if self.inject_failure == "code" and not self.injected:
            self.injected = True
            self.induced_now = True
            return "ERROR: the code runner crashed unexpectedly (process killed, exit code -9). No output was produced."
        return run_code(code, self.data_path, self.run_dir, self._code_calls)

    def _run_log_appendix(self) -> str:
        """Facts about the run, written by the framework (not the LLM), so they are always accurate."""
        calls = ", ".join(f"{n} x{c}" for n, c in self.counts.items())
        lines = [
            "", "---", "## Run log (added automatically by the framework)", "",
            f"- Plan versions written: {len(self.plans)}",
            f"- Tool calls: {calls}",
            f"- Tool failures: {self.failures}",
        ]
        for f in self.failure_log:
            tag = " (induced on purpose to test recovery)" if f["induced"] else ""
            lines.append(f"  - Step {f['step']}, {f['tool']}{tag}: {f['error']}")
        return "\n".join(lines) + "\n"

    def _finish(self, report: str) -> str:
        path = self.run_dir / "report.md"
        path.write_text(report.rstrip() + "\n" + self._run_log_appendix(), encoding="utf-8")
        self.finished = True
        self.report_path = path
        return f"Report saved to {path}."
