# Autonomous Data Analyst Agent

An AI agent that takes a CSV file and a goal in plain English, then works on its own: it inspects the data, plans, writes and runs its own Python code, fixes its own errors, and delivers a Markdown report with charts.

There are no hard-coded answers or rules about columns. Every decision comes from an LLM. The code only provides tools and a loop.

## How it works

```
Goal + CSV
    |
    v
+-----------------------------+
| LLM chooses the next action |<-----------+
+--------------+--------------+            |
               v                           |
   inspect_dataset | run_python | finish   |
               v                           |
   result (or error) goes back to LLM -----+
```

| Stage | What happens |
|---|---|
| Perceive | `inspect_dataset` profiles the file: shape, types, missing values, statistics, sample rows |
| Reason | The LLM explains its plan, then picks a tool |
| Act | `run_python` executes LLM-written code in a separate process (60s timeout) |
| Self-correct | Errors and suspicious output are returned to the LLM, which diagnoses and retries |
| Finish | The LLM decides when it has enough evidence and calls `finish` with the report |

The agent is a plain Python tool-calling loop (the ReAct pattern) with no agent framework, so every line is visible in `agent/`.

## Project structure

```
autonomous-data-agent/
├── main.py              # command-line entry point
├── agent/
│   ├── loop.py          # the reasoning loop, retries and step limit
│   ├── tools.py         # tool schemas and implementations
│   ├── sandbox.py       # runs generated code in a subprocess with a timeout
│   └── prompts.py       # system prompt
├── sample_data/         # synthetic sales.csv and the script that made it
├── outputs/             # one folder per run (report, charts, scripts, log)
├── requirements.txt
└── .env.example
```

## Installation

Requires Python 3.10 or newer.

1. Get the code and open a terminal in the project folder.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # Mac/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your settings file: copy `.env.example` to `.env` and fill in your key.

   ```
   LLM_API_KEY=your-key
   LLM_BASE_URL=
   LLM_MODEL=gpt-4o-mini
   ```

   The agent uses the OpenAI-compatible chat API, so these providers work by changing only these lines:

   | Provider | LLM_BASE_URL | LLM_MODEL (example) |
   |---|---|---|
   | OpenAI | *(leave empty)* | `gpt-4o-mini` |
   | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash` |
   | Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
   | Ollama (local) | `http://localhost:11434/v1` | any tool-capable model |

   The model must support tool/function calling.

## Usage

```bash
python main.py --data sample_data/sales.csv --goal "Find what drives units sold and summarize the top 3 insights"
```

Options: `--max-steps 15` (step limit), `--model NAME`, `--out outputs`.

Each run creates `outputs/run_<timestamp>/` containing:

- `report.md` - the final report
- `charts/` - charts the agent made
- `scripts/` - every Python script the agent wrote and ran
- `run_log.jsonl` - each action and its result, so the reasoning is auditable

You can use your own CSV: `python main.py --data my_file.csv --goal "..."`.

## Example run

```
=== Step 1/15 ===
Action: inspect_dataset
Result: Rows: 600, Columns: 6

Columns (dtype, missing, unique):
- date: str, missing=0, unique=600
- region: str, missing=0, unique=4
- price: float64, missing=0, unique=541
- discount_pct: int64, missing=0, unique=4
- marketing_spend: float64, missing=25, unique=527
- units_sold: float64, missing=0, unique=164

Numeric summary:
                 count      mean       std     min       25%      50%        ...

=== Step 2/15 ===
Action: run_python
Result: exit code: 0
STDOUT:
count     600.000000
mean      171.965000
std       344.732454
min        44.000000
25%       120.000000
50%       142.000000
75%       173.000000
max      5000.000000
Name: units_sold, dtype: float64
           date region  price  discount_pct  marketing_spend  units_sold
83   2025-03-25   West  60.63             0           1722.0      5000.0
519  2026-06-04   East  40.05    ...

=== Step 3/15 ===
Action: run_python
Result: exit code: 1
STDERR:
Traceback (most recent call last):
  File "C:\Users\kalra\OneDrive\Desktop\Projects\autonomous-data-agent\outputs\run_20261120_025653\scripts\step_02.py", line 27, in <module>
    beta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
                               ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
  File "C:\Users\kalra\OneDrive\Desktop\Projects\autonomous-data-agent\ve ...

=== Step 4/15 ===
Action: run_python
Result: exit code: 0
STDOUT:
intercept: 217.9009
price: -2.1379
discount_pct: 3.0963
marketing_spend: 0.0199
region_North: -20.7101
region_South: -43.5420
region_West: -18.7159
R-squared: 0.8799

=== Step 5/15 ===
Action: run_python
Result: exit code: 1
STDERR:
Traceback (most recent call last):
  File "C:\Users\kalra\OneDrive\Desktop\Projects\autonomous-data-agent\outputs\run_20261120_025653\scripts\step_04.py", line 8, in <module>
    import seaborn as sns # seaborn is typically available but let's stick to matplotlib for safety
    ^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'seaborn'

=== Step 6/15 ===
Action: run_python
Result: exit code: 0
New chart files saved: charts/marketing_vs_sales.png, charts/price_vs_sales.png
(no output - use print() to see results)

=== Step 7/15 ===
Action: run_python
Result: exit code: 0
STDOUT:
price  discount_pct  marketing_spend  units_sold
price            1.000000     -0.015297        -0.005325   -0.461109
discount_pct    -0.015297      1.000000        -0.014686    0.480340
marketing_spend -0.005325     -0.014686         1.000000    0.548658
units_sold      -0.461109      0.480340         0.548658    1.000000

=== Step 8/15 ===
Action: finish
Result: Report saved to C:\Users\kalra\OneDrive\Desktop\Projects\autonomous-data-agent\outputs\run_20261120_025653\report.md.

Done. Report: C:\Users\kalra\OneDrive\Desktop\Projects\autonomous-data-agent\outputs\run_20261120_025653\report.md
```

## Safeguards

- **Step limit:** the loop stops after `--max-steps`, and the agent is told when its last step arrives.
- **Timeout:** generated code is killed after 60 seconds.
- **Error recovery:** tool errors, bad JSON arguments and API failures (retried with backoff) never crash the run; the LLM sees the error and adapts.
- **Output truncation:** long outputs are shortened so the LLM context is not flooded.

## Limitations

- The sandbox is process isolation with a timeout, not a hardened sandbox. Run the agent only on data and with models you trust; do not expose it to untrusted users.
- Only CSV input is supported.
- Each code run is a fresh process, so the LLM reloads the data each time.
- Report quality depends on the model you choose. Weak models make weaker analyses.
- Statistical findings are exploratory, not proof of causation.

## Originality

All code in this repository was written for this project. It uses only the standard OpenAI Python SDK, pandas, numpy, matplotlib and python-dotenv.
