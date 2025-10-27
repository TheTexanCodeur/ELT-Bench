import yaml
import json
import os
import shutil

databases = [f.name for f in os.scandir('../elt-bench') if f.is_dir()]
databases.sort()

for db in databases:
  os.makedirs('../data/inputs',exist_ok=True)
  directory_path = f'../data/inputs/{db}'
  if os.path.exists(directory_path) and os.path.isdir(directory_path):
        shutil.rmtree(directory_path)
  os.system(f"cp -r ../elt-bench/{db} ../data/inputs")
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