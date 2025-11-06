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
python run.py --suffix eltbench --model gpt-5 --example_index 0-4
```



## Outputs
Results and logs mirror `spider-agent`, stored under `output/<timestamp>/<db>/sot/`.
