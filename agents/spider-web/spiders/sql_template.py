import os

# ------------------------------------------------------------
# Helper used inside all templates
# ------------------------------------------------------------

# Ensures absolute paths like "/workspace/foo.csv" → "./foo.csv"
NORMALIZE = "os.path.join('.', {path}.lstrip('/'))"


# ============================================================
# BIGQUERY TEMPLATES
# ============================================================

BQ_GET_TABLES_TEMPLATE = """
import os
import pandas as pd
from google.cloud import bigquery

# Load local credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./bigquery_credential.json"
client = bigquery.Client()

query = f\"\"\"
SELECT
    table_name, ddl
FROM
    `{database_name}.{dataset_name}.INFORMATION_SCHEMA.TABLES`
WHERE
    table_type != 'VIEW'
\"\"\"

query_job = client.query(query)

save_path = os.path.join(".", "{save_path}".lstrip("/"))

try:
    results = query_job.result().to_dataframe()
    if results.empty:
        print("No data found for the specified query.")
    else:
        results.to_csv(save_path, index=False)
        print(f"DB metadata is saved to {save_path}")
except Exception as e:
    print("Error occurred while fetching data: ", e)
"""


BQ_GET_TABLE_INFO_TEMPLATE = """
import os
import pandas as pd
from google.cloud import bigquery

# Load local credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./bigquery_credential.json"
client = bigquery.Client()

query = f\"\"\"
    SELECT field_path, data_type, description
    FROM `{database_name}.{dataset_name}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
    WHERE table_name = '{table}';
\"\"\"

query_job = client.query(query)

save_path = os.path.join(".", "{save_path}".lstrip("/"))

try:
    df = query_job.result().to_dataframe()
    if df.empty:
        print("No data found for the specified query.")
    else:
        df.to_csv(save_path, index=False)
        print(f"Results saved to {save_path}")
except Exception as e:
    print("Error occurred while fetching data: ", e)
"""


BQ_SAMPLE_ROWS_TEMPLATE = """
import os
import pandas as pd
from google.cloud import bigquery
import json

# Load local credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./bigquery_credential.json"
client = bigquery.Client()

query = f\"\"\"
SELECT *
FROM `{database_name}.{dataset_name}.{table}`
TABLESAMPLE SYSTEM (0.0001 PERCENT)
LIMIT {row_number};
\"\"\"

query_job = client.query(query)

save_path = os.path.join(".", "{save_path}".lstrip("/"))

try:
    df = query_job.result().to_dataframe()
    if df.empty:
        print("No data found for the specified query.")
    else:
        sample_rows = df.to_dict(orient='records')
        json_data = json.dumps(sample_rows, indent=4, default=str)
        with open(save_path, 'w') as fh:
            fh.write(json_data)
        print(f"Sample rows saved to {save_path}")
except Exception as e:
    print("Error occurred while fetching data: ", e)
"""


BQ_EXEC_SQL_QUERY_TEMPLATE = """
import os
import pandas as pd
from google.cloud import bigquery

# Load local credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./bigquery_credential.json"
client = bigquery.Client()

sql_query = f\"\"\"{sql_query}\"\"\"

query_job = client.query(sql_query)

save_path = os.path.join(".", "{save_path}".lstrip("/"))

try:
    df = query_job.result().to_dataframe()
    if df.empty:
        print("No data found for the provided query.")
    else:
        if {is_save}:
            df.to_csv(save_path, index=False)
            print(f"Results saved to {save_path}")
        else:
            print(df)
except Exception as e:
    print("Error occurred while executing SQL: ", e)
"""


# ============================================================
# SNOWFLAKE TEMPLATES
# ============================================================

SF_EXEC_SQL_QUERY_TEMPLATE = """
import os
import json
import pandas as pd
import snowflake.connector

# Load Snowflake credentials (local)
snowflake_credential = json.load(open("./snowflake_credential.json"))

# Connect
conn = snowflake.connector.connect(**snowflake_credential)
cursor = conn.cursor()

sql_query = f\"\"\"

{sql_query}

\"\"\"

# Execute
cursor.execute(sql_query)

save_path = os.path.join(".", "{save_path}".lstrip("/"))

try:
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(results, columns=columns)
    if df.empty:
        print("No data found for the specified query.")
    else:
        if {is_save}:
            df.to_csv(save_path, index=False)
            print(f"Results saved to {save_path}")
        else:
            print(df)
except Exception as e:
    print("Error: ", e)
finally:
    cursor.close()
    conn.close()
"""


SF_GET_TABLE_INFO_TEMPLATE = """
import os
import json
import pandas as pd
import snowflake.connector

# Load credentials locally
snowflake_credential = json.load(open("./snowflake_credential.json"))

conn = snowflake.connector.connect(**snowflake_credential)
cursor = conn.cursor()

query = f\"\"\"
SELECT
    column_name,
    data_type,
    comment
FROM
    "{database_name}".INFORMATION_SCHEMA.COLUMNS
WHERE
    table_schema = '{schema_name}'
    AND table_name = '{table}'
\"\"\"

cursor.execute(query)
save_path = os.path.join(".", "{save_path}".lstrip("/"))

try:
    df = pd.DataFrame(cursor.fetchall(), columns=['column_name', 'data_type', 'description'])
    if df.empty:
        print("No data found.")
    else:
        df.to_csv(save_path, index=False)
        print(f"Results saved to {save_path}")
except Exception as e:
    print("Error:", e)
finally:
    cursor.close()
    conn.close()
"""


SF_GET_TABLES_TEMPLATE = """
import os
import json
import pandas as pd
import snowflake.connector

# Local credentials
snowflake_credential = json.load(open("./snowflake_credential.json"))

conn = snowflake.connector.connect(**snowflake_credential)
cursor = conn.cursor()

query = f\"\"\"
SELECT table_name, comment
FROM "{database_name}".INFORMATION_SCHEMA.TABLES
WHERE table_schema = '{schema_name}'
\"\"\"

cursor.execute(query)
tables = cursor.fetchall()

df = pd.DataFrame(tables, columns=['table_name', 'description'])

save_path = os.path.join(".", "{save_path}".lstrip("/"))
df.to_csv(save_path, index=False)
print(f"Results saved to {save_path}")

cursor.close()
conn.close()
"""


SF_SAMPLE_ROWS_TEMPLATE = """
import os
import json
import pandas as pd
import snowflake.connector

# Local credentials
snowflake_credential = json.load(open("./snowflake_credential.json"))

conn = snowflake.connector.connect(**snowflake_credential)
cursor = conn.cursor()

query = f\"\"\"
SELECT *
FROM "{database_name}"."{schema_name}"."{table}"
TABLESAMPLE BERNOULLI (1)
LIMIT {row_number};
\"\"\"

cursor.execute(query)
rows = cursor.fetchall()
cols = [desc[0] for desc in cursor.description]

df = pd.DataFrame(rows, columns=cols)

save_path = os.path.join(".", "{save_path}".lstrip("/"))

import json
sample_rows = df.to_dict(orient='records')
json_data = json.dumps(sample_rows, indent=4, default=str)

with open(save_path, 'w') as fh:
    fh.write(json_data)

print(f"Sample rows saved to {save_path}")

cursor.close()
conn.close()
"""


# ============================================================
# LOCAL SQL TEMPLATE
# ============================================================

LOCAL_SQL_TEMPLATE = """
import pandas as pd
import os
import sqlite3
import duckdb

def detect_db_type(file_path):
    if file_path.endswith('.db') or file_path.endswith('.sqlite'):
        return 'sqlite'
    elif file_path.endswith('.duckdb'):
        return 'duckdb'
    else:
        try:
            conn = duckdb.connect(database=file_path, read_only=True)
            conn.execute('SELECT 1')
            conn.close()
            return 'duckdb'
        except:
            return 'sqlite'

def execute_sql(file_path, command, output_path):
    # Normalize paths
    file_path = os.path.join(".", file_path.lstrip("/"))
    output_path = os.path.join(".", output_path.lstrip("/"))

    db_type = detect_db_type(file_path)
    if db_type == 'sqlite' and not os.path.exists(file_path):
        print(f"ERROR: Database file not found: {file_path}")
        return

    conn = sqlite3.connect(file_path) if db_type == 'sqlite' else duckdb.connect(database=file_path, read_only=True)

    try:
        df = pd.read_sql_query(command, conn)
        if output_path.lower().endswith(".csv"):
            df.to_csv(output_path, index=False)
            print(f"Output saved to: {output_path}")
        else:
            print(df)
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        conn.close()

file_path = "{file_path}"
command = f\"\"\"{sql_command}\"\"\"
output_path = "{output_path}"

execute_sql(file_path, command, output_path)
"""
