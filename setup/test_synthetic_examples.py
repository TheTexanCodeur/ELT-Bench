"""
Test script to verify synthetic example generation works correctly.
"""

import os
import yaml
import glob
import csv


def test_example_rows_present():
    """Check that example rows are present in all data models."""
    inputs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'inputs')
    data_model_files = glob.glob(os.path.join(inputs_path, '**', 'data_model.yaml'), recursive=True)
    
    total_models = 0
    models_with_examples = 0
    models_without_examples = []
    
    for data_model_path in sorted(data_model_files):
        with open(data_model_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'models' not in data:
            continue
        
        db_name = os.path.basename(os.path.dirname(data_model_path))
        
        for model in data['models']:
            total_models += 1
            model_name = model.get('name', 'unknown')
            
            if 'example_row' in model and model['example_row']:
                models_with_examples += 1
            else:
                models_without_examples.append(f"{db_name}/{model_name}")
    
    print(f"Total models: {total_models}")
    print(f"Models with example rows: {models_with_examples}")
    print(f"Coverage: {100 * models_with_examples / total_models:.1f}%")
    
    if models_without_examples:
        print(f"\nModels without example rows ({len(models_without_examples)}):")
        for model in models_without_examples[:10]:  # Show first 10
            print(f"  - {model}")
        if len(models_without_examples) > 10:
            print(f"  ... and {len(models_without_examples) - 10} more")
    
    return models_with_examples == total_models


def test_example_row_structure():
    """Verify that example rows have the correct structure."""
    inputs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'inputs')
    data_model_files = glob.glob(os.path.join(inputs_path, '**', 'data_model.yaml'), recursive=True)
    
    issues = []
    
    for data_model_path in sorted(data_model_files):
        with open(data_model_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'models' not in data:
            continue
        
        db_name = os.path.basename(os.path.dirname(data_model_path))
        
        for model in data['models']:
            model_name = model.get('name', 'unknown')
            
            if 'example_row' not in model:
                continue
            
            example_row = model['example_row']
            
            # Check that example row is a dict
            if not isinstance(example_row, dict):
                issues.append(f"{db_name}/{model_name}: example_row is not a dict")
                continue
            
            # Check that all columns are present
            columns = model.get('columns', [])
            column_names = {col['name'] for col in columns}
            example_keys = set(example_row.keys())
            
            # Check for missing columns
            missing = column_names - example_keys
            if missing:
                issues.append(f"{db_name}/{model_name}: missing columns in example_row: {missing}")
            
            # Check for extra columns (not necessarily an error, but worth noting)
            extra = example_keys - column_names
            if extra:
                issues.append(f"{db_name}/{model_name}: extra columns in example_row: {extra}")
    
    if issues:
        print(f"\nStructure issues found ({len(issues)}):")
        for issue in issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
    else:
        print("\nAll example rows have correct structure!")
    
    return len(issues) == 0


def test_no_ground_truth_leakage():
    """Verify that example rows don't match any ground truth rows."""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inputs_path = os.path.join(base_path, 'data', 'inputs')
    gt_path = os.path.join(base_path, 'data', 'gt')
    
    data_model_files = glob.glob(os.path.join(inputs_path, '**', 'data_model.yaml'), recursive=True)
    
    leaks = []
    checked = 0
    skipped = []
    
    for data_model_path in sorted(data_model_files):
        with open(data_model_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'models' not in data:
            continue
        
        db_name = os.path.basename(os.path.dirname(data_model_path))
        db_gt_path = os.path.join(gt_path, db_name)
        
        if not os.path.exists(db_gt_path):
            continue
        
        for model in data['models']:
            model_name = model.get('name', '').lower()
            
            if 'example_row' not in model or not model['example_row']:
                continue
            
            example_row = model['example_row']
            
            # Read ground truth CSV (try both lowercase and capitalized)
            gt_csv = os.path.join(db_gt_path, f"{model_name}.csv")
            if not os.path.exists(gt_csv):
                # Try capitalized version
                gt_csv = os.path.join(db_gt_path, f"{model_name.capitalize()}.csv")
            
            if not os.path.exists(gt_csv):
                skipped.append(f"{db_name}/{model_name}")
                continue
            
            checked += 1
            
            try:
                with open(gt_csv, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    
                    # Check if example matches any ground truth row
                    for gt_row in reader:
                        # Compare rows (case-insensitive keys, string comparison of values)
                        example_normalized = {k.upper(): str(v) if v is not None else '' for k, v in example_row.items()}
                        gt_normalized = {k.upper(): str(v).strip() if v else '' for k, v in gt_row.items()}
                        
                        # Check if all values match
                        if all(example_normalized.get(k) == gt_normalized.get(k) for k in example_normalized.keys()):
                            leaks.append(f"{db_name}/{model_name}: example matches ground truth row")
                            break
            except Exception as e:
                # Skip if we can't read the ground truth
                pass
    
    print(f"Checked {checked} models against ground truth")
    
    if skipped:
        print(f"Skipped {len(skipped)} models (no ground truth CSV found):")
        for skip in skipped:
            print(f"  - {skip}")
    
    if leaks:
        print(f"\n⚠️ Data leakage detected ({len(leaks)}):")
        for leak in leaks[:10]:
            print(f"  - {leak}")
        if len(leaks) > 10:
            print(f"  ... and {len(leaks) - 10} more")
    else:
        print("\n✓ No ground truth leakage detected!")
    
    return len(leaks) == 0


def main():
    """Run all tests."""
    print("Testing Synthetic Example Generation")
    print("=" * 50)
    
    print("\nTest 1: Example rows present")
    print("-" * 50)
    test1_passed = test_example_rows_present()
    
    print("\nTest 2: Example row structure")
    print("-" * 50)
    test2_passed = test_example_row_structure()
    
    print("\nTest 3: No ground truth leakage")
    print("-" * 50)
    test3_passed = test_no_ground_truth_leakage()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed and test3_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
        if not test1_passed:
            print("  - Not all models have example rows")
        if not test2_passed:
            print("  - Some example rows have structure issues")
        if not test3_passed:
            print("  - Data leakage detected!")


if __name__ == "__main__":
    main()
