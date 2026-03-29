"""
Generate synthetic example rows for each data model to help agents understand
the expected output format without data leakage from ground truth.

This script uses an LLM to generate realistic example rows based on:
- The data model schema (column names and descriptions)
- A few rows from the ground truth (for reference)
- Instructions to modify values to prevent data leakage
"""

import os
import yaml
import csv
import glob
from openai import OpenAI
import json
from typing import Dict, List, Any


def read_ground_truth_sample(gt_path: str, model_name: str, num_rows: int = 3) -> List[Dict[str, Any]]:
    """Read a sample of rows from the ground truth CSV."""
    csv_file = os.path.join(gt_path, f"{model_name}.csv")
    
    if not os.path.exists(csv_file):
        return []
    
    rows = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= num_rows:
                break
            rows.append(row)
    
    return rows


def generate_synthetic_row(model: Dict[str, Any], gt_samples: List[Dict[str, Any]], client: OpenAI) -> Dict[str, Any]:
    """Use an LLM to generate a synthetic example row based on the model schema and ground truth samples."""
    
    # Build the prompt
    model_name = model.get('name', 'unknown')
    model_description = model.get('description', '')
    columns = model.get('columns', [])
    
    columns_text = "\n".join([
        f"  - {col['name']}: {col.get('description', 'No description')}"
        for col in columns
    ])
    
    gt_text = ""
    if gt_samples:
        gt_text = "\n\nHere are some example rows from the actual data (for reference only - DO NOT copy these values):\n"
        for i, row in enumerate(gt_samples, 1):
            gt_text += f"\nExample {i}:\n"
            gt_text += json.dumps(row, indent=2)
    
    prompt = f"""You are generating a synthetic example row for a data transformation task.

Model: {model_name}
Description: {model_description}

Columns:
{columns_text}
{gt_text}

Generate ONE realistic example row that demonstrates the expected output format. 
The values should be:
- Realistic and consistent with the column descriptions
- Different from any real data (to avoid data leakage)
- Helpful for understanding what each column should contain
- Properly formatted (numbers as numbers, strings as strings, etc.)

Return ONLY a valid JSON object with the column names as keys. Use null for NULL values.
Do not include any explanation or markdown formatting."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates synthetic data examples."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            if content.startswith("json"):
                content = content[4:].strip()
        
        synthetic_row = json.loads(content)
        return synthetic_row
        
    except Exception as e:
        print(f"Error generating synthetic row for {model_name}: {e}")
        # Return empty example if generation fails
        return {col['name']: None for col in columns}


def update_data_model_with_examples(data_model_path: str, gt_base_path: str, client: OpenAI):
    """Update a data_model.yaml file with synthetic example rows."""
    
    if not os.path.exists(data_model_path):
        print(f"Skipping {data_model_path} - file not found")
        return
    
    # Read the data model
    with open(data_model_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data or 'models' not in data:
        print(f"Skipping {data_model_path} - no models found")
        return
    
    # Get the database name from the path
    db_name = os.path.basename(os.path.dirname(data_model_path))
    gt_path = os.path.join(gt_base_path, db_name)
    
    # Process each model
    for model in data['models']:
        model_name = model.get('name', '').lower()
        
        if not model_name:
            continue
        
        # Read ground truth samples
        gt_samples = read_ground_truth_sample(gt_path, model_name)
        
        # Generate synthetic example
        print(f"Generating synthetic example for {db_name}/{model_name}...")
        synthetic_example = generate_synthetic_row(model, gt_samples, client)
        
        # Add to model
        model['example_row'] = synthetic_example
    
    # Write back to file
    with open(data_model_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=float('inf'))
    
    print(f"Updated {data_model_path} with synthetic examples")


def main():
    """Generate synthetic examples for all data models."""
    
    # Initialize OpenAI client
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    client = OpenAI(api_key=api_key)
    
    # Paths
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gt_base_path = os.path.join(base_path, 'data', 'gt')
    inputs_path = os.path.join(base_path, 'data', 'inputs')
    
    # Find all data_model.yaml files
    data_model_files = glob.glob(os.path.join(inputs_path, '**', 'data_model.yaml'), recursive=True)
    
    print(f"Found {len(data_model_files)} data model files")
    
    for data_model_path in sorted(data_model_files):
        try:
            update_data_model_with_examples(data_model_path, gt_base_path, client)
        except Exception as e:
            print(f"Error processing {data_model_path}: {e}")
    
    print("\nSynthetic example generation complete!")


if __name__ == "__main__":
    main()
