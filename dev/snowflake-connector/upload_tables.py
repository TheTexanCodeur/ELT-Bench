import snowflake.connector
import os
import argparse
import shutil
import yaml
import requests
import json
from pathlib import Path
import unicodedata

# Get current working directory (you said you're at "ELT-BENCH" level)
base_path = Path.cwd()

parser = argparse.ArgumentParser()
parser.add_argument("--example_index", "-i", type=str, default="all", help="index range of the examples to run, e.g., '0-10', '2,3', 'all'")
args = parser.parse_args()


def select_tables(example_index):
    if "-" in example_index:
        # Handle range like "0-10"
        start, end = map(int, example_index.split("-"))
        return start, end + 1


def read_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def load_flat_files(db_name):
    folder_path = f"./elt-bench/{db_name}"
    config_path = os.path.join(folder_path, "config.yaml")
    
    # Read config file
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    flat_files = config.get('flat_files', [])
    
    if not flat_files:
        print("No flat files found in config", flush=True)
        return
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(folder_path, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    for file_config in flat_files:
        table_name = file_config['table']
        file_format = file_config['format']
        file_url = file_config['path']
        
        print(f"\n{'='*60}", flush=True)
        print(f"Processing: {table_name} ({file_format})", flush=True)
        print(f"{'='*60}", flush=True)
        
        # Download file
        local_file = os.path.join(data_dir, f"{table_name}.{file_format}")
        print(f"Downloading from {file_url}...", flush=True)
        
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        
        with open(local_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(local_file)
        print(f"✓ Downloaded {file_size:,} bytes", flush=True)
        
    #DB data
    for file in os.listdir(data_dir):
        
        # Build the path
        file_path = base_path / "elt-bench" / db_name / "data" / file

        # Normalize Unicode (so é is handled correctly)
        normalized_path = unicodedata.normalize("NFC", str(file_path.resolve()))
        
        # Convert to file:// URI
        file_uri = Path(normalized_path).resolve().as_uri()
        
        file_path = file_uri
    
        file_info = file.split(".")
        file_name = file_info[0]
        file_type = file_info[1]
        
        conn.cursor().execute("REMOVE @loading_stage")
        conn.cursor().execute(f"PUT {file_path} @loading_stage")
        
        file_format = file_type_dict.get(file_type)
        
        conn.cursor().execute(
        f"CREATE OR REPLACE TABLE {file_name} "
        "USING TEMPLATE("
        "SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*)) "
        "FROM "
        "TABLE("
        "INFER_SCHEMA("
        "LOCATION => '@loading_stage',"
        f"FILE_FORMAT => '{file_format}')))")
        
        # Rename columns to uppercase
        columns = conn.cursor().execute(f"DESC TABLE {file_name}").fetchall()
        for col in columns:
            old_name = col[0]
            new_name = old_name.upper()
            if old_name != new_name:
                conn.cursor().execute(f'ALTER TABLE {file_name} RENAME COLUMN "{old_name}" TO "{new_name}"')
        
        conn.cursor().execute(
        f"COPY INTO {file_name} "
        "FROM @loading_stage "
        f"FILE_FORMAT = '{file_format}' "
        "MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE")
        
        conn.cursor().execute("REMOVE @loading_stage")
        
        print(f"Finished loading file {file_name}", flush=True)
    
    shutil.rmtree(data_dir)

file_path = './setup/destination/snowflake_credential.json' 
snowflake_config = read_json(file_path)   

conn = snowflake.connector.connect(**snowflake_config) 
    
file_type_dict = {"csv": "CSV_TYPE", "jsonl": "JSON_TYPE", "parquet": "PARQUET_TYPE"}

names = sorted(os.listdir("./elt-bench"))

start, end = select_tables(args.example_index)

for folder_name in names[start:end]:
        
    folder_path = f"./data/source/db/data/{folder_name}"
    
    conn.cursor().execute(f"DROP DATABASE IF EXISTS {folder_name}")

    conn.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {folder_name}")
    conn.cursor().execute(f"USE DATABASE {folder_name}")
    conn.cursor().execute("CREATE SCHEMA IF NOT EXISTS AIRBYTE_SCHEMA")
    conn.cursor().execute(f"USE SCHEMA {folder_name}.AIRBYTE_SCHEMA")
    conn.cursor().execute("CREATE STAGE IF NOT EXISTS loading_stage")

    conn.cursor().execute("""CREATE OR ALTER FILE FORMAT CSV_TYPE 
                          TYPE=CSV 
                          FIELD_DELIMITER = ','
                          PARSE_HEADER = TRUE
                          FIELD_OPTIONALLY_ENCLOSED_BY = '"' 
                          ESCAPE = NONE
                          ESCAPE_UNENCLOSED_FIELD = NONE """)
    
    conn.cursor().execute("CREATE OR ALTER FILE FORMAT PARQUET_TYPE TYPE=PARQUET")
    conn.cursor().execute("CREATE OR ALTER FILE FORMAT JSON_TYPE TYPE=JSON")
    
    load_flat_files(folder_name)
    
    if os.path.isdir(folder_path):

        #DB data
        for file in os.listdir(folder_path):
            
            # Build the path dynamically
            file_path = base_path / "data" / "source" / "db" / "data" / folder_name / file
            
            # Normalize the entire path (base + subfolders + filename)
            normalized_path = unicodedata.normalize("NFC", str(file_path))
            
            # Convert to file:// URI
            file_uri = Path(normalized_path).resolve().as_uri()

            #file_path = f"file:///Users/quentinsandoz/Repos/ELT-Bench/setup/data/{folder_name}/{file}"
            
            file_path = file_uri
            
            file_info = file.split(".")
            file_name = file_info[0]
            file_type = file_info[1]
            
            conn.cursor().execute("REMOVE @loading_stage")
            conn.cursor().execute(f"PUT {file_path} @loading_stage")
            
            file_format = file_type_dict.get(file_type)
            
            conn.cursor().execute(
            f"CREATE OR REPLACE TABLE {file_name} "
            "USING TEMPLATE("
            "SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*)) "
            "FROM "
            "TABLE("
            "INFER_SCHEMA("
            "LOCATION => '@loading_stage',"
            f"FILE_FORMAT => '{file_format}')))")
            
            # Rename columns to uppercase
            columns = conn.cursor().execute(f"DESC TABLE {file_name}").fetchall()
            for col in columns:
                old_name = col[0]
                new_name = old_name.upper()
                if old_name != new_name:
                    conn.cursor().execute(f'ALTER TABLE {file_name} RENAME COLUMN "{old_name}" TO "{new_name}"')
            
            conn.cursor().execute(
            f"COPY INTO {file_name} "
            "FROM @loading_stage "
            f"FILE_FORMAT = '{file_format}' "
            "MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE")
            
            conn.cursor().execute("REMOVE @loading_stage")
            
            print(f"Finished loading file {file_name}", flush=True)
        
    folder_path = f"./data/source/api/data/{folder_name}"
    
    if os.path.isdir(folder_path):
        
        #API Data
        for file in os.listdir(folder_path):
            
            # Build the path dynamically
            file_path = base_path / "data" / "source" / "api" / "data" /folder_name / file

            
            # Normalize the entire path (base + subfolders + filename)
            normalized_path = unicodedata.normalize("NFC", str(file_path))
        
            # Convert to file:// URI
            file_uri = Path(normalized_path).resolve().as_uri()
            
            file_path = file_uri

            #file_path = f"file:///Users/quentinsandoz/Repos/ELT-Bench/elt-docker/rest_api/data/{folder_name}/{file}"
            
            file_info = file.split(".")
            file_name = file_info[0]
            file_type = file_info[1]
            
            conn.cursor().execute("REMOVE @loading_stage")
            conn.cursor().execute(f"PUT {file_path} @loading_stage ")
            
            file_format = file_type_dict.get(file_type)
            
            conn.cursor().execute(
            f"CREATE OR REPLACE TABLE {file_name} "
            "USING TEMPLATE("
            "SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*)) "
            "FROM "
            "TABLE("
            "INFER_SCHEMA("
            "LOCATION => '@loading_stage',"
            f"FILE_FORMAT => '{file_format}')))")
            
            # Rename columns to uppercase
            columns = conn.cursor().execute(f"DESC TABLE {file_name}").fetchall()
            for col in columns:
                old_name = col[0]
                new_name = old_name.upper()
                if old_name != new_name:
                    conn.cursor().execute(f'ALTER TABLE {file_name} RENAME COLUMN "{old_name}" TO "{new_name}"')
            
            conn.cursor().execute(
            f"COPY INTO {file_name} "
            "FROM @loading_stage "
            f"FILE_FORMAT = '{file_format}' "
            "MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE")
            
            conn.cursor().execute("REMOVE @loading_stage")
            
            print(f"Finished loading file {file_name}", flush=True)
    
    print(f"Finished DB {folder_name}", flush=True)