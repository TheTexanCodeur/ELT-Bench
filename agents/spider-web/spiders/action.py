#coding=utf8
import re
from dataclasses import dataclass, field
from typing import Optional, Any
from abc import ABC

def remove_quote(text: str) -> str:
    """ 
    If the text is wrapped by a pair of quote symbols, remove them.
    In the middle of the text, the same quote symbol should remove the '/' escape character.
    """
    for quote in ['"', "'", "`"]:
        if text.startswith(quote) and text.endswith(quote):
            text = text[1:-1]
            text = text.replace(f"\\{quote}", quote)
            break
    return text.strip()

def normalize_path(path: str) -> str:
    """
    Normalizes file paths by:
    - Removing redundant separators and up-level references
    - Converting /workspace/ to relative paths
    - Keeping other paths as-is but normalized
    
    Examples:
      /workspace/foo.csv  → foo.csv
      /foo.csv            → foo.csv
      foo.csv             → foo.csv
      ./foo.csv           → foo.csv
      ././foo.csv         → foo.csv
    """
    if not path:
        return path
    
    import os
    path = path.strip()
    
    # Remove /workspace/ prefix if present
    if path.startswith("/workspace/"):
        path = path[len("/workspace/"):]
    elif path.startswith("/workspace"):
        path = path[len("/workspace"):]
    
    # Remove leading / to make it relative
    if path.startswith("/"):
        path = path[1:]
    
    # Normalize to remove ./ and ././ patterns
    path = os.path.normpath(path)
    
    # If normpath returned '.', make it empty or keep as needed
    if path == '.':
        return '.'
    
    return path


# ============================================================
# Base Action
# ============================================================

@dataclass
class Action(ABC):
    
    action_type: str = field(
        repr=False,
        metadata={"help": 'type of action, e.g. "exec_code", "create_file", "terminate"'}
    )


    @classmethod
    def get_action_description(cls) -> str:
        return """
Action: action format
Description: detailed definition of this action type.
Usage: example cases
Observation: the observation space of this action type.
"""

    @classmethod
    def parse_action_from_text(cls, text: str) -> Optional[Any]:
        raise NotImplementedError

@dataclass
class Bash(Action):

    action_type: str = field(
        default="exec_code",
        init=False,
        repr=False,
        metadata={"help": 'type of action, c.f., "exec_code"'}
    )

    code: str = field(
        metadata={"help": 'command to execute'}
    )

    @classmethod
    def get_action_description(cls) -> str:
        return """
## Bash Action
* Signature: Bash(code="shell_command")
* Description: This action string will execute a valid shell command in the `code` field. Only non-interactive commands are supported. Commands like "vim" and viewing images directly (e.g., using "display") are not allowed.
* Example: Bash(code="ls -l")
"""

    @classmethod
    def parse_action_from_text(cls, text: str) -> Optional[Action]:
        pattern = r'Bash\(code="((?:\\.|[^"\\])*)"\)'
        matches = re.findall(pattern, text, flags=re.DOTALL)
        if matches:
            code = matches[-1]
            return cls(code=cls.remove_quote(code))
        return None

    @staticmethod
    def remove_quote(s: str) -> str:
        return bytes(s, "utf-8").decode("unicode_escape")
    
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(code="{self.code}")'
    
    

@dataclass
class CreateFile(Action):

    action_type: str = field(
        default="create_file",
        init=False,
        repr=False,
        metadata={"help": 'type of action, c.f., "create_file"'}
    )

    code: str = field(
        metadata={"help": 'code to write into file'}
    )

    filepath: Optional[str] = field(
        default=None,
        metadata={"help": 'name of file to create'}
    )

    def __repr__(self) -> str:
        return f"CreateFile(filepath=\"{self.filepath}\"):\n```\n{self.code.strip()}\n```"

    @classmethod
    def get_action_description(cls) -> str:
        return """
## CreateFile
Signature: CreateFile(filepath="path/to/file"):
```
file_content
```
Description: This action will create a file in the field `filepath` with the content wrapped by paired ``` symbols. Make sure the file content is complete and correct. If the file already exists, you can only use EditFile to modify it.
Example: CreateFile(filepath="hello_world.py"):
```
print("Hello, world!")
```
"""

    def __post_init__(self):
        self.filepath = normalize_path(self.filepath)

    @classmethod
    def parse_action_from_text(cls, text: str):
        # Matches CreateFile(filepath=xxx) with content in ```
        matches = re.findall(
            r'CreateFile\(filepath=(.*?)\).*?```[ \t]*\w*[ \t]*\r?\n(.*?)[\r\n \t]*```',
            text,
            flags=re.DOTALL,
        )
        if matches:
            filepath_raw, code_raw = matches[-1]
            return cls(
                code=code_raw.strip(),
                filepath=normalize_path(remove_quote(filepath_raw.strip()))
            )
        return None
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(filepath='{self.filepath}':\n'''\n{self.code}\n''')"
       
@dataclass
class EditFile(Action):
    action_type: str = field(default="edit_file",init=False,repr=False,metadata={"help": 'type of action, c.f., "edit_file"'})

    code: str = field(metadata={"help": 'code to write into file'})

    filepath: Optional[str] = field(default=None,metadata={"help": 'name of file to edit'})

    def __repr__(self) -> str:
        return f"EditFile(filepath=\"{self.filepath}\"):\n```\n{self.code.strip()}\n```"


    def __post_init__(self):
        self.filepath = normalize_path(self.filepath)

    @classmethod
    def parse_action_from_text(cls, text: str):
        matches = re.findall(
            r'EditFile\(filepath=(.*?)\).*?```[ \t]*\w*[ \t]*\r?\n(.*?)[\r\n \t]*```',
            text,
            flags=re.DOTALL,
        )
        if matches:
            filepath_raw, code_raw = matches[-1]
            return cls(
                code=code_raw.strip(),
                filepath=normalize_path(remove_quote(filepath_raw.strip()))
            )
        return None

    def __repr__(self):
        return f"EditFile(filepath=\"{self.filepath}\"):\n```\n{self.code.strip()}\n```"


# ============================================================
# LOCAL_DB_SQL
# ============================================================

@dataclass
class LOCAL_DB_SQL(Action):
    action_type: str = field(default="sql_command", init=False, repr=False)
    code: str = field()
    file_path: str = field(default=None)
    output: str = field(default=None)

    def __post_init__(self):
        self.file_path = normalize_path(self.file_path)
        self.output = normalize_path(self.output)

    @classmethod
    def parse_action_from_text(cls, text: str):
        matches = re.findall(
            r'LOCAL_DB_SQL\(file_path=(.*?), command=(.*?), output=(.*?)\)',
            text,
            flags=re.DOTALL
        )
        if matches:
            file_path, command, output = (item.strip() for item in matches[-1])
            return cls(
                file_path=remove_quote(file_path),
                code=remove_quote(command),
                output=remove_quote(output)
            )
        return None


# ============================================================
# BIGQUERY_EXEC_SQL
# ============================================================

@dataclass
class BIGQUERY_EXEC_SQL(Action):
    action_type: str = field(default="execute_bigquery_SQL", init=False, repr=False)
    sql_query: str = field()
    is_save: bool = field()
    save_path: str = field(default=None)

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def parse_action_from_text(cls, text: str):
        pattern = (
            r'BIGQUERY_EXEC_SQL\(sql_query=(?P<quote>\"\"\"|\"|\'|\"\"|\'\')'
            r'(.*?)(?P=quote), is_save=(True|False)'
            r'(, save_path=(?P<quote2>\"|\'|\"\"|\'\')(.*?)(?P=quote2))?\)'
        )
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            sql_query = match.group(2).strip()
            is_save = match.group(3).strip().lower() == 'true'
            save_path = match.group(6) if match.group(6) else ""
            return cls(
                sql_query=sql_query,
                is_save=is_save,
                save_path=save_path
            )
        return None


# ============================================================
# SNOWFLAKE_EXEC_SQL
# ============================================================

@dataclass
class SNOWFLAKE_EXEC_SQL(Action):
    action_type: str = field(default="execute_snowflake_SQL", init=False, repr=False)
    sql_query: str = field()
    is_save: bool = field()
    save_path: str = field(default=None)

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def get_action_description(cls) -> str:
        return """
## SNOWFLAKE_EXEC_SQL
* Signature: SNOWFLAKE_EXEC_SQL(sql_query="SELECT * FROM table", is_save=True, save_path="./path/to/output.csv")
* Description: Executes a SQL query on Snowflake. If is_save=True, results are saved to the specified CSV file. If is_save=False, results are printed to console.
* Example: SNOWFLAKE_EXEC_SQL(sql_query="SELECT * FROM ADDRESS.AIRBYTE_SCHEMA.STATES LIMIT 10", is_save=True, save_path="./results.csv")
"""

    @classmethod
    def parse_action_from_text(cls, text: str):
        pattern = r'''
            SNOWFLAKE_EXEC_SQL\(
                \s*sql_query\s*=\s*
                (?P<quote_sql>\"\"\"|\"|\'\'\'|\'|\"\"\" )
                (?P<sql_query>.*?)
                (?<!\\)(?P=quote_sql)
                ,\s*is_save\s*=\s*
                (?P<is_save>True|False)
                (?:,\s*save_path\s*=\s*
                    (?P<quote_path>\"\"\"|\"|\'\'\'|\'|\"\"\" )
                    (?P<save_path>.*?)
                    (?<!\\)(?P=quote_path)
                )?
                \s*\)
        '''
        match = re.search(pattern, text, flags=re.DOTALL | re.VERBOSE)
        if match:
            sql_raw = match.group('sql_query')
            sql_query = sql_raw.replace(r'\"', '"').replace(r"\'", "'").replace('\\\\', '\\')
            is_save = match.group('is_save').lower() == "true"

            save_path = ""
            if match.group('save_path'):
                sp_raw = match.group('save_path')
                save_path = sp_raw.replace(r'\"', '"').replace(r"\'", "'").replace('\\\\', '\\')

            return cls(
                sql_query=sql_query,
                is_save=is_save,
                save_path=save_path
            )
        return None


# ============================================================
# SF_GET_TABLES
# ============================================================

@dataclass
class SF_GET_TABLES(Action):
    action_type: str = field(default="get_tables", init=False, repr=False)
    database_name: str = field()
    schema_name: str = field()
    save_path: str = field()

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def get_action_description(cls) -> str:
        return """
## SF_GET_TABLES
* Signature: SF_GET_TABLES(database_name="DATABASE", schema_name="SCHEMA", save_path="./path/to/output.csv")
* Description: Retrieves the list of tables in the specified Snowflake database and schema. Results are saved to a CSV file.
* Example: SF_GET_TABLES(database_name="ADDRESS", schema_name="AIRBYTE_SCHEMA", save_path="./samples/_tables.csv")
"""

    @classmethod
    def parse_action_from_text(cls, text: str):
        m = re.findall(r'SF_GET_TABLES\(database_name=(.*?), schema_name=(.*?), save_path=(.*?)\)', text, flags=re.DOTALL)
        if m:
            db, schema, sp = (item.strip() for item in m[-1])
            return cls(
                database_name=remove_quote(db),
                schema_name=remove_quote(schema),
                save_path=remove_quote(sp)
            )
        return None


# ============================================================
# SF_GET_TABLE_INFO
# ============================================================

@dataclass
class SF_GET_TABLE_INFO(Action):
    action_type: str = field(default="get_table_info", init=False, repr=False)
    database_name: str = field()
    schema_name: str = field()
    table: str = field()
    save_path: str = field()

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def get_action_description(cls) -> str:
        return """
## SF_GET_TABLE_INFO
* Signature: SF_GET_TABLE_INFO(database_name="DATABASE", schema_name="SCHEMA", table="TABLE_NAME", save_path="./path/to/output.csv")
* Description: Retrieves column information (column names, data types, comments) for a specific table in Snowflake. Results are saved to a CSV file.
* Example: SF_GET_TABLE_INFO(database_name="ADDRESS", schema_name="AIRBYTE_SCHEMA", table="STATES", save_path="./schemas/states_info.csv")
"""

    @classmethod
    def parse_action_from_text(cls, text: str):
        m = re.findall(r'SF_GET_TABLE_INFO\(database_name=(.*?), schema_name=(.*?), table=(.*?), save_path=(.*?)\)', text, flags=re.DOTALL)
        if m:
            db, schema, table, sp = (item.strip() for item in m[-1])
            return cls(
                database_name=remove_quote(db),
                schema_name=remove_quote(schema),
                table=remove_quote(table),
                save_path=remove_quote(sp)
            )
        return None


# ============================================================
# BQ_GET_TABLES
# ============================================================

@dataclass
class BQ_GET_TABLES(Action):
    action_type: str = field(default="get_tables", init=False, repr=False)
    database_name: str = field()
    dataset_name: str = field()
    save_path: str = field()

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def parse_action_from_text(cls, text: str):
        m = re.findall(r'GET_TABLES\(database_name=(.*?), dataset_name=(.*?), save_path=(.*?)\)', text, flags=re.DOTALL)
        if m:
            db, dataset, sp = (item.strip() for item in m[-1])
            return cls(
                database_name=remove_quote(db),
                dataset_name=remove_quote(dataset),
                save_path=remove_quote(sp)
            )
        return None


# ============================================================
# BQ_GET_TABLE_INFO
# ============================================================

@dataclass
class BQ_GET_TABLE_INFO(Action):
    action_type: str = field(default="get_table_info", init=False, repr=False)
    database_name: str = field()
    dataset_name: str = field()
    table: str = field()
    save_path: str = field()

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def parse_action_from_text(cls, text: str):
        m = re.findall(r'GET_TABLE_INFO\(database_name=(.*?), dataset_name=(.*?), table=(.*?), save_path=(.*?)\)', text, flags=re.DOTALL)
        if m:
            db, dataset, table, sp = (item.strip() for item in m[-1])
            return cls(
                database_name=remove_quote(db),
                dataset_name=remove_quote(dataset),
                table=remove_quote(table),
                save_path=remove_quote(sp)
            )
        return None


# ============================================================
# BQ_SAMPLE_ROWS
# ============================================================

@dataclass
class BQ_SAMPLE_ROWS(Action):
    action_type: str = field(default="bq_sample_rows", init=False, repr=False)
    database_name: str = field()
    dataset_name: str = field()
    table: str = field()
    row_number: int = field()
    save_path: str = field()

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def parse_action_from_text(cls, text: str):
        m = re.findall(
            r'BQ_SAMPLE_ROWS\(database_name=(.*?), dataset_name=(.*?), table=(.*?), row_number=(.*?), save_path=(.*?)\)',
            text, flags=re.DOTALL
        )
        if m:
            db, dataset, table, rn, sp = (item.strip() for item in m[-1])
            return cls(
                database_name=remove_quote(db),
                dataset_name=remove_quote(dataset),
                table=remove_quote(table),
                row_number=int(rn),
                save_path=remove_quote(sp)
            )
        return None


# ============================================================
# SF_SAMPLE_ROWS
# ============================================================

@dataclass
class SF_SAMPLE_ROWS(Action):
    action_type: str = field(default="sf_sample_rows", init=False, repr=False)
    database_name: str = field()
    schema_name: str = field()
    table: str = field()
    row_number: int = field()
    save_path: str = field()

    def __post_init__(self):
        self.save_path = normalize_path(self.save_path)

    @classmethod
    def get_action_description(cls) -> str:
        return """
## SF_SAMPLE_ROWS
* Signature: SF_SAMPLE_ROWS(database_name="DATABASE", schema_name="SCHEMA", table="TABLE_NAME", row_number=10, save_path="./path/to/output.json")
* Description: Retrieves sample rows from a Snowflake table using TABLESAMPLE. Results are saved as JSON.
* Example: SF_SAMPLE_ROWS(database_name="ADDRESS", schema_name="AIRBYTE_SCHEMA", table="STATES", row_number=5, save_path="./samples/states.json")
"""

    @classmethod
    def parse_action_from_text(cls, text: str):
        m = re.findall(
            r'SF_SAMPLE_ROWS\(database_name=(.*?), schema_name=(.*?), table=(.*?), row_number=(.*?), save_path=(.*?)\)',
            text, flags=re.DOTALL
        )
        if m:
            db, schema, table, rn, sp = (item.strip() for item in m[-1])
            return cls(
                database_name=remove_quote(db),
                schema_name=remove_quote(schema),
                table=remove_quote(table),
                row_number=int(rn),
                save_path=remove_quote(sp)
            )
        return None


# ============================================================
# Terminate
# ============================================================

@dataclass
class Terminate(Action):
    action_type: str = field(default="terminate", init=False, repr=False)
    output: Optional[str] = field(default=None)
    code: str = field(default="")

    @classmethod
    def get_action_description(cls) -> str:
        return """
## Terminate
* Signature: Terminate(output="result_message")
* Description: Terminates the task and returns the final result message.
* Example: Terminate(output="Task completed successfully")
"""

    @classmethod
    def parse_action_from_text(cls, text: str):
        m = re.findall(r'Terminate\(output=(.*?)\)', text, flags=re.DOTALL)
        if m:
            return cls(output=remove_quote(m[-1]))
        return None

    def __repr__(self):
        return f'Terminate(output="{self.output}")'
