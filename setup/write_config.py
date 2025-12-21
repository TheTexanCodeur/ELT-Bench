import yaml
import json
import os
import shutil
import csv
import glob

def uppercase_csv_files(directory):
    """
    Convert all CSV file names and their column names to uppercase
    to avoid Snowflake case sensitivity issues.
    """
    csv_files = glob.glob(os.path.join(directory, '**', '*.csv'), recursive=True)
    
    for csv_file in csv_files:
        # Read the CSV file
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)   
            
            if len(rows) > 0:
                # Convert header (column names) to uppercase
                rows[1:] = [[row[0].upper(), row[1]] for row in rows[1:]]
              
                # Write back to the same file
                with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
                    
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
        
        # Rename file to uppercase
        file_dir = os.path.dirname(csv_file)
        file_name = os.path.basename(csv_file)
        new_file_name = file_name.upper()
        
        if file_name != new_file_name:
            new_file_path = os.path.join(file_dir, new_file_name)
            try:
                os.rename(csv_file, new_file_path)
            except Exception as e:
                print(f"Error renaming {csv_file}: {e}")


def uppercase_data_model_yaml(yaml_file_path):
    """
    Convert all model names and column names in data_model.yaml to uppercase
    to match Snowflake case conventions.
    """
    if not os.path.exists(yaml_file_path):
        return
    
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data and 'models' in data:
            for model in data['models']:
                # Convert model name to uppercase
                if 'name' in model:
                    model['name'] = model['name'].upper()
                
                # Convert column names to uppercase
                if 'columns' in model:
                    for column in model['columns']:
                        if 'name' in column:
                            column['name'] = column['name'].upper()
        
        # Write back to file with proper encoding
        with open(yaml_file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=float('inf'))
        
    except Exception as e:
        print(f"Error processing {yaml_file_path}: {e}")
        
        
def uppercase_config_yaml(yaml_file_path):
    """
    Convert all model names and column names in data_model.yaml to uppercase
    to match Snowflake case conventions.
    """
    if not os.path.exists(yaml_file_path):
        return
      
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data and 'snowflake' in data:
            if 'config' in data['snowflake'] and 'database' in data['snowflake']['config']:
                data['snowflake']['config']['database'] = data['snowflake']['config']['database'].upper()
              
        # Write back to file with proper encoding
        with open(yaml_file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=float('inf'))
        
    except Exception as e:
        print(f"Error processing {yaml_file_path}: {e}")
        

databases = [f.name for f in os.scandir('../elt-bench') if f.is_dir()]
databases.sort()

for db in databases:
  os.makedirs('../data/inputs',exist_ok=True)
  directory_path = f'../data/inputs/{db}'
  if os.path.exists(directory_path) and os.path.isdir(directory_path):
        shutil.rmtree(directory_path)
  os.system(f"cp -r ../elt-bench/{db} ../data/inputs")
  
  # Convert CSV files and columns to uppercase
  uppercase_csv_files(directory_path)
  
  # Convert data_model.yaml model and column names to uppercase
  data_model_path = f'../data/inputs/{db}/data_model.yaml'
  uppercase_data_model_yaml(data_model_path)
  
  # Convert config.yaml snowflake database name to uppercase
  config_path = f'../data/inputs/{db}/config.yaml'
  uppercase_config_yaml(config_path)
  
  with open(f'../data/inputs/{db}/config.yaml', 'r') as file:
    config_data = yaml.safe_load(file)

  with open('./destination/snowflake_credential.json', 'r') as file:
    snowflake_credential = json.load(file)

  # Update Snowflake configuration only (Airbyte config removed - EL handled separately)
  config_data['snowflake']['config']['account'] = snowflake_credential['account']

  with open(f'../data/inputs/{db}/config.yaml', 'w') as file:
    yaml.dump(config_data, file)
    
  new_sf_credentials = {}
  new_sf_credentials['account'] = snowflake_credential['account']
  new_sf_credentials['user'] = "AIRBYTE_USER"
  new_sf_credentials['password'] = "Snowflake@123"

  with open(f'../data/inputs/{db}/snowflake_credential.json', 'w') as file:
    json.dump(new_sf_credentials, file)

  # EL stage files removed - agents only handle transformation now
  # Previously copied: documentation/, check_job_status.py, elt/main.tf