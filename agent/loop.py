"""The agent loop: the LLM chooses an action, we run it, and feed the result back."""
import json
import os
import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, ToolBox


def make_client() -> OpenAI:
    key = os.getenv("LLM_API_KEY")
    if not key:
        raise SystemExit("LLM_API_KEY is not set. Copy .env.example to .env and fill it in.")
    base_url = os.getenv("LLM_BASE_URL") or None
    return OpenAI(api_key=key, base_url=base_url)


def _short(text: str, n: int = 600) -> str:
    text = str(text)
    return text if len(text) <= n else text[:n] + " ..."


def _chat_with_retry(client, **kwargs):
    waits = [10, 30, 60, 90, 120]
    for attempt in range(len(waits) + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            status = getattr(e, "status_code", None)
            if status in (400, 401, 403, 404):
                detail = getattr(e, "body", None) or getattr(getattr(e, "response", None), "text", "")
                raise SystemExit(f"Request rejected ({status}).\n{e}\n{detail}")
            if attempt == len(waits):
                detail = getattr(e, "body", None) or getattr(getattr(e, "response", None), "text", "")
                raise SystemExit(f"Gave up after retries ({status}).\n{e}\n{detail}")
            wait = waits[attempt]
            print(f"  [LLM call failed: {type(e).__name__}. Retrying in {wait}s]")
            time.sleep(wait)


def run_agent(goal: str, data_path: Path, out_root: Path, model: str, max_steps: int = 15, client=None):
    client = client or make_client()
    run_dir = out_root / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    tools = ToolBox(data_path.resolve(), run_dir.resolve())
    log = open(run_dir / "run_log.jsonl", "w", encoding="utf-8")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Goal: {goal}\n\nDataset file: {data_path.name}"},
    ]

    for step in range(1, max_steps + 1):
        if step == max_steps:
            messages.append({"role": "user", "content": "This is your LAST step. Call finish now with your best report."})
        if step > 1:
            time.sleep(4)
        print(f"\n=== Step {step}/{max_steps} ===")
        resp = _chat_with_retry(client, model=model, messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto")
        msg = resp.choices[0].message
        calls = msg.tool_calls or []

        if msg.content:
            print(f"Agent: {_short(msg.content)}")

        assistant = {"role": "assistant", "content": msg.content or None}
        if calls:
            assistant["tool_calls"] = [c.model_dump(exclude_none=True) for c in calls]
        messages.append(assistant)

        if not calls:
            messages.append({"role": "user", "content": "Continue working with your tools, or call finish if done."})
            continue

        for c in calls:
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
                result = "ERROR: tool arguments were not valid JSON. Try again."
            else:
                print(f"Action: {c.function.name}")
                result = tools.call(c.function.name, args)
            print(f"Result: {_short(result, 400)}")
            messages.append({"role": "tool", "tool_call_id": c.id, "content": result})
            log.write(json.dumps({"step": step, "tool": c.function.name, "args": args, "result": result}) + "\n")

        if tools.finished:
            break

    log.close()
    if tools.finished:
        print(f"\nDone. Report: {tools.report_path}")
    else:
        print("\nStopped: step limit reached without a final report.")
    return tools.report_path
