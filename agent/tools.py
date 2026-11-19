"""Tools the LLM can call, plus their JSON schemas."""
from pathlib import Path

import pandas as pd

from .sandbox import run_code

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_dataset",
            "description": "Profile the dataset: shape, column types, missing values, statistics and sample rows.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Run Python code in a fresh process and return stdout/stderr. "
                "Predefined: DATA_PATH, OUTPUT_DIR, CHARTS_DIR. Reload data each call."
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


class ToolBox:
    def __init__(self, data_path: Path, run_dir: Path):
        self.data_path = data_path
        self.run_dir = run_dir
        self.finished = False
        self.report_path = None
        self._code_calls = 0

    def call(self, name: str, args: dict) -> str:
        try:
            if name == "inspect_dataset":
                return self._inspect()
            if name == "run_python":
                self._code_calls += 1
                return run_code(args["code"], self.data_path, self.run_dir, self._code_calls)
            if name == "finish":
                return self._finish(args["report_markdown"])
            return f"ERROR: unknown tool '{name}'."
        except KeyError as e:
            return f"ERROR: missing required argument {e}."
        except Exception as e:  # tool failures go back to the LLM, not crash the run
            return f"ERROR: {type(e).__name__}: {e}"

    def _inspect(self) -> str:
        df = pd.read_csv(self.data_path)
        out = [f"Rows: {len(df)}, Columns: {df.shape[1]}", "", "Columns (dtype, missing, unique):"]
        for col in df.columns:
            out.append(f"- {col}: {df[col].dtype}, missing={int(df[col].isna().sum())}, unique={df[col].nunique()}")
        num = df.select_dtypes("number")
        if not num.empty:
            out += ["", "Numeric summary:", num.describe().round(3).T.to_string()]
        cat = df.select_dtypes(exclude="number")
        for col in cat.columns[:8]:
            top = df[col].value_counts().head(5).to_dict()
            out.append(f"\nTop values of {col}: {top}")
        out += ["", "First 5 rows:", df.head(5).to_string()]
        return "\n".join(out)

    def _finish(self, report: str) -> str:
        path = self.run_dir / "report.md"
        path.write_text(report, encoding="utf-8")
        self.finished = True
        self.report_path = path
        return f"Report saved to {path}."
