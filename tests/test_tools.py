"""Tests for the tools, the plan guard, failure injection and the code sandbox."""
import json

import pytest

from agent import tools as tools_module
from agent.sandbox import run_code
from agent.tools import ToolBox, is_failure
from agent.web import FetchError


@pytest.fixture()
def box(tmp_path):
    csv = tmp_path / "d.csv"
    csv.write_text("a,b,c\n1,2,x\n2,4,y\n3,,x\n")
    run = tmp_path / "run"
    run.mkdir()
    return ToolBox(csv, run)


def test_tools_refuse_to_work_before_a_plan_exists(box):
    result = box.call("inspect_dataset", {})
    assert result.startswith("ERROR") and "make_plan" in result


def test_make_plan_records_and_writes_plan_file(box):
    box.call("make_plan", {"steps": ["look at data", "analyse"]})
    assert len(box.plans) == 1
    assert "1. look at data" in box.last_plan_text
    box.call("make_plan", {"steps": ["new approach"], "revision_reason": "source failed"})
    assert len(box.plans) == 2 and "REVISED PLAN v2" in box.last_plan_text
    assert "source failed" in (box.run_dir / "plan.md").read_text()


def test_make_plan_rejects_bad_input(box):
    assert box.call("make_plan", {"steps": []}).startswith("ERROR")
    assert box.call("make_plan", {"steps": "not a list"}).startswith("ERROR")


def test_inspect_csv_reports_missing_values(box):
    box.call("make_plan", {"steps": ["x"]})
    out = box.call("inspect_dataset", {})
    assert "Rows: 3" in out and "b: float64, missing=1" in out


def test_inspect_without_any_data_explains_the_problem(tmp_path):
    b = ToolBox(None, tmp_path)
    b.call("make_plan", {"steps": ["x"]})
    assert b.call("inspect_dataset", {}).startswith("ERROR")


def test_run_python_success_and_error_are_reported(box):
    box.call("make_plan", {"steps": ["x"]})
    ok = box.call("run_python", {"code": "print(1+1)"})
    assert ok.startswith("exit code: 0") and "2" in ok
    bad = box.call("run_python", {"code": "print(undefined_name)"})
    assert is_failure(bad) and "NameError" in bad
    assert box.failures == 1


def test_sandbox_timeout(tmp_path):
    out = run_code("import time; time.sleep(5)", None, tmp_path, 1, timeout=1)
    assert out.startswith("ERROR") and "time limit" in out


def test_sandbox_exposes_predefined_variables(tmp_path):
    out = run_code("print(DATA_PATH, DATA_DIR.endswith('data'), CHARTS_DIR.endswith('charts'))", None, tmp_path, 1)
    assert "None True True" in out


def test_unknown_tool_and_missing_argument(box):
    box.call("make_plan", {"steps": ["x"]})
    assert "unknown tool" in box.call("nope", {})
    assert "missing required argument" in box.call("run_python", {})


def test_fetch_saves_file_and_inspect_reads_json(box, monkeypatch):
    monkeypatch.setattr(tools_module, "safe_fetch", lambda url: (200, "application/json", b'{"daily": {"t": [1, 2, 3]}}'))
    box.call("make_plan", {"steps": ["x"]})
    out = box.call("fetch_url", {"url": "https://example.org/api", "save_as": "../evil name.json"})
    assert "Saved as" in out and "evil_name.json" in out        # path tricks are neutralised
    assert (box.data_dir / "evil_name.json").exists()
    assert "list of 3 items" in box.call("inspect_dataset", {"path": "evil_name.json"})


def test_fetch_error_is_returned_as_text(box, monkeypatch):
    def boom(url):
        raise FetchError("HTTP 404 Not Found")
    monkeypatch.setattr(tools_module, "safe_fetch", boom)
    box.call("make_plan", {"steps": ["x"]})
    out = box.call("fetch_url", {"url": "https://example.org/missing"})
    assert out == "ERROR: HTTP 404 Not Found" and box.failures == 1


def test_injected_fetch_failure_happens_exactly_once(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_module, "safe_fetch", lambda url: (200, "application/json", b"{}"))
    b = ToolBox(None, tmp_path, inject_failure="fetch")
    b.call("make_plan", {"steps": ["x"]})
    first = b.call("fetch_url", {"url": "https://example.org"})
    assert first.startswith("ERROR") and b.induced_now
    second = b.call("fetch_url", {"url": "https://example.org"})
    assert second.startswith("HTTP 200") and not b.induced_now


def test_injected_code_failure_happens_exactly_once(tmp_path):
    b = ToolBox(None, tmp_path, inject_failure="code")
    b.call("make_plan", {"steps": ["x"]})
    assert b.call("run_python", {"code": "print(1)"}).startswith("ERROR")
    assert b.call("run_python", {"code": "print(1)"}).startswith("exit code: 0")


def test_finish_writes_report(box):
    box.call("make_plan", {"steps": ["x"]})
    box.call("finish", {"report_markdown": "# Done"})
    assert box.finished
    text = (box.run_dir / "report.md").read_text()
    assert text.startswith("# Done") and "## Run log" in text and "Tool failures: 0" in text


def test_report_appendix_lists_failures_and_induced_ones(tmp_path):
    b = ToolBox(None, tmp_path, inject_failure="code")
    b.call("make_plan", {"steps": ["x"]})
    b.current_step = 2
    b.call("run_python", {"code": "print(1)"})                 # induced
    b.current_step = 3
    b.call("run_python", {"code": "raise ValueError('bad column')"})   # real failure
    b.call("finish", {"report_markdown": "# R"})
    text = (tmp_path / "report.md").read_text()
    assert "Tool failures: 2" in text
    assert "Step 2, run_python (induced on purpose to test recovery)" in text
    assert "Step 3, run_python: ValueError: bad column" in text


def test_is_failure():
    assert is_failure("ERROR: boom")
    assert is_failure("exit code: 1\nSTDERR: x")
    assert is_failure("exit code: -9")
    assert not is_failure("exit code: 0\nSTDOUT: ok")
