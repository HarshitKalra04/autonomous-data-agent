"""End-to-end tests of the agent loop using a scripted fake LLM (no API key needed)."""
import json
from pathlib import Path
from types import SimpleNamespace as NS

from agent import tools as tools_module
from agent.loop import run_agent

CSV = Path(__file__).resolve().parent.parent / "sample_data" / "sales.csv"


class FakeCall:
    def __init__(self, i, name, args):
        self.id = f"call{i}"
        self.function = NS(name=name, arguments=json.dumps(args))
        self._d = {"id": self.id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}

    def model_dump(self, **kwargs):
        return self._d


def reply(content, *calls):
    msg = NS(content=content, tool_calls=list(calls))
    return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=10, completion_tokens=5))


def fake_client(script):
    it = iter(script)
    return NS(chat=NS(completions=NS(create=lambda **kw: next(it))))


def test_agent_plans_recovers_from_code_error_and_finishes(tmp_path):
    script = [
        reply("Planning.", FakeCall(1, "make_plan", {"steps": ["inspect", "analyse", "report"]})),
        reply("Inspect.", FakeCall(2, "inspect_dataset", {})),
        reply("Try a bad column.", FakeCall(3, "run_python", {"code": "import pandas as pd\nprint(pd.read_csv(DATA_PATH)['nope'])"})),
        reply("Fix it.", FakeCall(4, "run_python", {"code": "import pandas as pd\nprint(pd.read_csv(DATA_PATH)['price'].mean())"})),
        reply("Done.", FakeCall(5, "finish", {"report_markdown": "# Report"})),
    ]
    run_dir = run_agent("test goal", CSV, tmp_path, "fake", 10, client=fake_client(script))

    summary = json.loads((run_dir / "run_summary.json").read_text())
    assert summary["finished"] and summary["steps_used"] == 5
    assert summary["tool_failures"] == 1 and summary["plan_versions"] == 1
    assert summary["tool_calls"]["run_python"] == 2
    assert summary["prompt_tokens"] == 50
    transcript = (run_dir / "transcript.txt").read_text()
    assert "PLAN v1" in transcript and "1. inspect" in transcript
    report = (run_dir / "report.md").read_text()
    assert report.startswith("# Report") and "Step 3, run_python" in report and "KeyError" in report
    assert (run_dir / "plan.md").exists() and (run_dir / "run_log.jsonl").exists()


def test_agent_refused_until_plan_then_recovers(tmp_path):
    script = [
        reply("Skipping the plan.", FakeCall(1, "inspect_dataset", {})),
        reply("OK, planning.", FakeCall(2, "make_plan", {"steps": ["inspect", "finish"]})),
        reply("Finish.", FakeCall(3, "finish", {"report_markdown": "# R"})),
    ]
    run_dir = run_agent("g", CSV, tmp_path, "fake", 10, client=fake_client(script))
    log = [json.loads(line) for line in (run_dir / "run_log.jsonl").read_text().splitlines()]
    assert log[0]["failure"] and "make_plan" in log[0]["result"]
    assert json.loads((run_dir / "run_summary.json").read_text())["finished"]


def test_induced_fetch_failure_is_recovered_and_marked(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_module, "safe_fetch", lambda url: (200, "application/json", b'{"x": [1, 2]}'))
    script = [
        reply("", FakeCall(1, "make_plan", {"steps": ["fetch", "report"]})),
        reply("", FakeCall(2, "fetch_url", {"url": "https://example.org/api"})),                 # induced failure
        reply("Retrying after the timeout.", FakeCall(3, "fetch_url", {"url": "https://example.org/api"})),
        reply("", FakeCall(4, "finish", {"report_markdown": "# R"})),
    ]
    run_dir = run_agent("g", None, tmp_path, "fake", 10, client=fake_client(script), inject_failure="fetch")
    summary = json.loads((run_dir / "run_summary.json").read_text())
    assert summary["failure_injection"] == {"mode": "fetch", "triggered": True}
    assert summary["tool_failures"] == 1 and summary["finished"]
    transcript = (run_dir / "transcript.txt").read_text()
    assert "[INDUCED FAILURE]" in transcript and "timed out" in transcript
    log = [json.loads(line) for line in (run_dir / "run_log.jsonl").read_text().splitlines()]
    assert [e["induced"] for e in log] == [False, True, False, False]


def test_step_limit_stops_the_run_without_a_report(tmp_path):
    script = [reply("thinking")] * 3
    run_dir = run_agent("g", CSV, tmp_path, "fake", 3, client=fake_client(script))
    summary = json.loads((run_dir / "run_summary.json").read_text())
    assert not summary["finished"] and summary["steps_used"] == 3
    assert "step limit reached" in (run_dir / "transcript.txt").read_text()


def test_bad_json_arguments_are_reported_back(tmp_path):
    bad = FakeCall(1, "make_plan", {})
    bad.function.arguments = "{not json"
    script = [
        reply("", bad),
        reply("", FakeCall(2, "make_plan", {"steps": ["a"]})),
        reply("", FakeCall(3, "finish", {"report_markdown": "# R"})),
    ]
    run_dir = run_agent("g", CSV, tmp_path, "fake", 10, client=fake_client(script))
    assert "not valid JSON" in (run_dir / "transcript.txt").read_text()
    assert json.loads((run_dir / "run_summary.json").read_text())["finished"]


def test_agent_is_told_todays_date(tmp_path):
    from datetime import date
    seen = {}

    calls = iter([
        reply("", FakeCall(1, "make_plan", {"steps": ["a"]})),
        reply("", FakeCall(2, "finish", {"report_markdown": "# R"})),
    ])

    def create(**kwargs):
        seen.setdefault("first", kwargs["messages"][1]["content"])
        return next(calls)

    client = NS(chat=NS(completions=NS(create=create)))
    run_agent("any goal", None, tmp_path, "fake", 5, client=client)
    assert date.today().isoformat() in seen["first"]
