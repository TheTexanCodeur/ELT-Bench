# Synthetic Example Rows

## Purpose

Augment each task with a synthetic example row showing the expected output format, without leaking ground truth data.

## Setup

```bash
cd setup
export OPENAI_API_KEY=your_key_here
bash elt_setup.sh  # Runs automatically during setup
```

Or run standalone:
```bash
python3 generate_synthetic_examples.py
```

## What It Does

Adds an `example_row` field to each model in `data_model.yaml`:

```yaml
models:
  - name: STATES
    columns:
      - name: ABBREVIATION
        description: the abbreviation of the state name
      # ... more columns ...
    example_row:
      ABBREVIATION: "TX"
      NAME: "Texas"
      NUM_COUNTIES: 254
      # ... synthetic values (not from ground truth)
```

## How It Works

1. Reads data model schema and a few ground truth samples
2. Uses GPT-4 to generate realistic but modified values
3. Adds synthetic example to `data_model.yaml`

## Agent Usage

```python
import yaml

with open('./data_model.yaml', 'r') as f:
    models = yaml.safe_load(f)['models']

for model in models:
    example = model.get('example_row', {})
    # Use example to understand format, infer types, validate structure
```

## Benefits

- **Disambiguation**: Clear output format
- **Type inference**: See which columns are int vs string
- **No data leakage**: Values differ from ground truth
- **Validation**: Check output structure matches expected schema

## Testing

```bash
python3 test_synthetic_examples.py
```

## Cost

~$1-2 for all databases (one-time during setup)
