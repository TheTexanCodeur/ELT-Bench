import json
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List

try:
    import snowflake.connector as sf
except Exception as e:
    sf = None


# --- identifier helpers -------------------------------------------------------

_VALID_IDENT = re.compile(r"^[A-Za-z0-9_]+$")

def _ident(name: str) -> str:
    """
    Validate a Snowflake identifier and return it for unquoted use.
    We intentionally DO NOT quote, so Snowflake folds to UPPERCASE and
    matches the usual DB/SCHEMA objects (like AIRLINE) even if you pass 'airline'.
    """
    if not name:
        raise ValueError("Empty identifier")
    if not _VALID_IDENT.match(name):
        raise ValueError(
            f"Invalid Snowflake identifier '{name}'. "
            "Allowed characters: letters, digits, underscore."
        )
    return name


# --- creds & connection -------------------------------------------------------

@dataclass
class SnowflakeCreds:
    account: str
    user: str
    password: str
    # Optional session params; use user defaults if omitted (same posture as spider)
    role: Optional[str] = None
    warehouse: Optional[str] = None
    database: Optional[str] = None
    schema: Optional[str] = None


def load_creds(path: str) -> SnowflakeCreds:
    with open(path, "r") as f:
        raw = json.load(f)
    return SnowflakeCreds(
        account=raw["account"],
        user=raw["user"],
        password=raw["password"],
        role=raw.get("role"),
        warehouse=raw.get("warehouse"),
        database=raw.get("database"),
        schema=raw.get("schema"),
    )


def connect(creds: SnowflakeCreds):
    if sf is None:
        raise RuntimeError("snowflake-connector-python not installed")
    kwargs = dict(account=creds.account, user=creds.user, password=creds.password)
    if creds.role:
        kwargs["role"] = creds.role
    if creds.warehouse:
        kwargs["warehouse"] = creds.warehouse
    if creds.database:
        kwargs["database"] = creds.database
    if creds.schema:
        kwargs["schema"] = creds.schema
    return sf.connect(**kwargs)


# --- execution helpers --------------------------------------------------------

def run_sql(
    creds_path: str,
    sql: str,
    database: Optional[str] = None,
    schema: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Execute SQL after setting context like spider does:
    - USE DATABASE <folder> if provided (UNQUOTED to avoid case-sensitivity)
    - USE SCHEMA <schema> if provided (UNQUOTED)
    """
    creds = load_creds(creds_path)
    conn = connect(creds)
    cur = conn.cursor()
    try:
        if database:
            cur.execute(f"USE DATABASE {_ident(database)}")
        if schema:
            cur.execute(f"USE SCHEMA {_ident(schema)}")

        cur.execute(sql)
        try:
            rows = cur.fetchall()
            return True, str(rows)
        except Exception:
            return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def fetch_tables(
    creds_path: str,
    database: Optional[str] = None,
    schema: Optional[str] = None,
) -> List[tuple]:
    """
    Return list of (table_name, column_name, data_type) from the current (or given) schema.
    Matches spider’s idea of “current DB is the folder name”; no AIRBYTE defaults.
    """
    creds = load_creds(creds_path)
    conn = connect(creds)
    cur = conn.cursor()
    try:
        if database:
            cur.execute(f"USE DATABASE {_ident(database)}")
        if schema:
            cur.execute(f"USE SCHEMA {_ident(schema)}")

        # Resolve active schema; if none, try PUBLIC (common default)
        cur.execute("SELECT CURRENT_SCHEMA()")
        (active_schema,) = cur.fetchone()
        if not active_schema:
            try:
                cur.execute("USE SCHEMA PUBLIC")
                active_schema = "PUBLIC"
            except Exception:
                # leave it None; query will likely return 0 rows
                active_schema = None

        if not active_schema:
            # No schema to inspect -> no tables
            return []

        # Pull columns for active schema
        q = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s
        ORDER BY table_name, ordinal_position
        """
        cur.execute(q, (active_schema,))
        rows = cur.fetchall()
        return rows
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
