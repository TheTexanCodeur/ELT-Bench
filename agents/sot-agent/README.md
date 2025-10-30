# SoT-Agent (SQL-of-Thought) — ELT-Bench (Transform Stage)

A drop-in agent for **ELT-Bench (Transform-only)** that wraps the **SQL-of-Thought** multi-agent pipeline.

## Quick start
```
conda create -n sot python=3.11 -y
conda activate sot
pip install -r requirements.txt

# API keys (example)
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export FIREWORKS_API_KEY=...
```

### Run on ELT-Bench (same CLI as spider-agent)
```
python run.py --suffix eltbench --model gpt-4o --example_index 0-4
```

By default, the agent discovers problems from `../../elt-bench/` and reads Snowflake creds from `../../setup/destination/snowflake_credential.json`, matching the benchmark layout.

## What this agent does
- Keeps the **full SoT stack** (schema linking → sub-problem identification → plan → SQL generation → guided error-correction with execution feedback).
- Writes final tables into **AIRBYTE_SCHEMA** in Snowflake, exactly as the evaluator expects.
- Leaves the rest of the benchmark untouched (no evaluator changes).

## Repo assumptions
Either:
1) Place the SQL-of-Thought repo as a sibling: `../SQL-of-Thought`, **or**
2) Set `SOT_PATH=/absolute/path/to/SQL-of-Thought`

The agent will import from there at runtime.

## Outputs
Results and logs mirror `spider-agent`, stored under `output/<timestamp>/<db>/sot/`.
