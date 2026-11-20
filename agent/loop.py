"""The agent loop: the LLM chooses an action, we run it, and feed the result back."""
import json
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, ToolBox, is_failure


def make_client() -> OpenAI:
    key = os.getenv("LLM_API_KEY")
    if not key:
        raise SystemExit("LLM_API_KEY is not set. Copy .env.example to .env and fill it in.")
    return OpenAI(api_key=key, base_url=os.getenv("LLM_BASE_URL") or None)


def _short(text, n: int = 600) -> str:
    text = str(text)
    return text if len(text) <= n else text[:n] + " ..."


class Transcript:
    """Prints to the console and keeps the same text in transcript.txt."""

    def __init__(self, path: Path):
        self._f = open(path, "w", encoding="utf-8")

    def say(self, text: str = "") -> None:
        print(text)
        self._f.write(text + "\n")
        self._f.flush()

    def close(self) -> None:
        self._f.close()


def _chat_with_retry(client, **kwargs):
    """Retry temporary API problems with growing waits; stop at once on permanent ones."""
    waits = [10, 30, 60, 90, 120]
    for attempt in range(len(waits) + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            status = getattr(e, "status_code", None)
            detail = getattr(e, "body", None) or getattr(getattr(e, "response", None), "text", "")
            if status in (400, 401, 403, 404):
                raise SystemExit(f"Request rejected ({status}). Check LLM_API_KEY and LLM_MODEL in your .env file.\n{e}\n{detail}")
            if attempt == len(waits):
                raise SystemExit(f"Gave up after retries ({status}).\n{e}\n{detail}")
            wait = waits[attempt]
            print(f"  [LLM call failed: {type(e).__name__}. Retrying in {wait}s]")
            time.sleep(wait)


def _describe_call(name: str, args: dict) -> str:
    if name == "fetch_url":
        return f"fetch_url  url={args.get('url')}"
    if name == "inspect_dataset" and args.get("path"):
        return f"inspect_dataset  path={args['path']}"
    return name


def run_agent(
    goal: str,
    data_path: Optional[Path],
    out_root: Path,
    model: str,
    max_steps: int = 15,
    client=None,
    inject_failure: Optional[str] = None,
    step_delay: float = 0.0,
) -> Path:
    client = client or make_client()
    started = time.time()
    run_dir = out_root / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    tools = ToolBox(data_path.resolve() if data_path else None, run_dir.resolve(), inject_failure)
    tr = Transcript(run_dir / "transcript.txt")
    log = open(run_dir / "run_log.jsonl", "w", encoding="utf-8")

    user_msg = f"Goal: {goal}\n\nToday's date is {date.today().isoformat()}.\n\n"
    if data_path:
        user_msg += f"A CSV dataset is provided: {data_path.name}. Use inspect_dataset to look at it."
    else:
        user_msg += "No dataset is provided. Source any data you need live with fetch_url (public APIs)."
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_msg}]

    tr.say(f"GOAL: {goal}")
    tr.say(f"MODEL: {model} | max steps: {max_steps} | data: {data_path.name if data_path else 'none (live sources)'}")
    if inject_failure:
        tr.say(f"[TEST MODE] failure injection enabled: first '{'fetch_url' if inject_failure == 'fetch' else 'run_python'}' call will fail on purpose")

    llm_requests = prompt_tokens = completion_tokens = 0
    steps_used = 0

    for step in range(1, max_steps + 1):
        steps_used = step
        if step > 1 and step_delay:
            time.sleep(step_delay)
        if step == max_steps:
            messages.append({"role": "user", "content": "This is your LAST step. Call finish now with your best report."})

        tr.say(f"\n=== Step {step}/{max_steps} ===")
        resp = _chat_with_retry(client, model=model, messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto")
        llm_requests += 1
        usage = getattr(resp, "usage", None)
        if usage:
            prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens += getattr(usage, "completion_tokens", 0) or 0

        tools.current_step = step
        msg = resp.choices[0].message
        calls = msg.tool_calls or []
        if msg.content:
            tr.say(f"Agent: {_short(msg.content)}")

        assistant = {"role": "assistant", "content": msg.content or (None if calls else "")}
        if calls:
            assistant["tool_calls"] = [c.model_dump(exclude_none=True) for c in calls]
        messages.append(assistant)

        if not calls:
            messages.append({"role": "user", "content": "Continue with your tools, or call finish if you are done."})
            continue

        for c in calls:
            induced = False
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
                result = "ERROR: tool arguments were not valid JSON. Try again."
                tr.say(f"Action: {c.function.name} (unreadable arguments)")
                tr.say(f"Result: {result}")
            else:
                name = c.function.name
                result = tools.call(name, args)
                if name == "make_plan" and not is_failure(result):
                    tr.say(tools.last_plan_text)
                    result_to_show = None
                else:
                    tr.say(f"Action: {_describe_call(name, args)}")
                    result_to_show = result
                induced = tools.induced_now
                if induced:
                    tr.say("[INDUCED FAILURE] this error was injected on purpose to test recovery")
                if result_to_show is not None:
                    tr.say(f"Result: {_short(result_to_show, 500)}")
            messages.append({"role": "tool", "tool_call_id": c.id, "content": result})
            log.write(json.dumps({
                "step": step, "tool": c.function.name, "args": args, "result": result,
                "failure": is_failure(result), "induced": induced,
            }) + "\n")

        if tools.finished:
            break

    log.close()
    summary = {
        "goal": goal,
        "model": model,
        "data_file": data_path.name if data_path else None,
        "finished": tools.finished,
        "steps_used": steps_used,
        "duration_seconds": round(time.time() - started, 1),
        "llm_requests": llm_requests,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tool_calls": tools.counts,
        "tool_failures": tools.failures,
        "plan_versions": len(tools.plans),
        "plans": tools.plans,
        "failure_injection": {"mode": inject_failure, "triggered": tools.injected} if inject_failure else None,
        "report": str(tools.report_path) if tools.report_path else None,
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if tools.finished:
        tr.say(f"\nDone in {steps_used} steps, {tools.failures} tool failure(s), {len(tools.plans)} plan version(s).")
        tr.say(f"Report: {tools.report_path}")
    else:
        tr.say("\nStopped: step limit reached without a final report.")
    if inject_failure and not tools.injected:
        tr.say("Note: the injected failure never triggered because that tool was not used in this run.")
    tr.close()
    return run_dir
