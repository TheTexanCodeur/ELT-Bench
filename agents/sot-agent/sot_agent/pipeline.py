from typing import Tuple, Optional, List
import json
import re
import os
import glob

from .llm import call_llm
from .snowflake_exec import run_sql, fetch_tables
from .agent import (
    SchemaLinkingAgent,
    SubproblemAgent,
    QueryPlanAgent,
    SQLAgent,
    CorrectionPlanAgent,
    CorrectionSQLAgent,
    LLMClient,
)

MAX_CRITIC_ATTEMPTS = 3


# ---------- minimal SoT-compatible helpers ----------

def clean_json(s: str):
    """
    Try to parse a JSON object/list out of an LLM response.
    Falls back to a best-effort extraction of the first {...} or [...] block.
    """
    if s is None:
        return {}
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r'(\{.*\}|\[.*\])', s, flags=re.DOTALL)
    if m:
        frag = m.group(1)
        try:
            return json.loads(frag)
        except Exception:
            pass
    return s


def postprocess_sql(sql: str) -> str:
    """Normalize the SQL emitted by LLMs."""
    if sql is None:
        return ""
    s = sql.strip()
    s = re.sub(r"^```(?:sql)?\s*|\s*```$", "", s, flags=re.IGNORECASE | re.DOTALL).strip()
    s = re.sub(r"^\s*(SQL\s*:\s*)", "", s, flags=re.IGNORECASE).strip()
    s = s.rstrip("; \n\t\r")
    return s


# ---------- workspace readers ----------

def _read_json_schemas(work_dir: str) -> str:
    """
    Read data/inputs/<problem>/schemas/*.json and render a compact text.
    Each JSON can be either {table: {...}} or {"table": "name", "columns": [...], "pks": [...], "fks": [...] }.
    We accept flexible shapes and print what we find.
    """
    buf = []
    schema_dir = os.path.join(work_dir, "schemas")
    for path in sorted(glob.glob(os.path.join(schema_dir, "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # try common shapes
        if isinstance(data, dict) and "table" in data:
            t = data.get("table")
            cols = data.get("columns") or data.get("cols") or []
            pks = data.get("pks") or data.get("primary_keys") or data.get("primary_key") or []
            fks = data.get("fks") or data.get("foreign_keys") or []
            cols_str = ", ".join([c if isinstance(c, str) else c.get("name", "") for c in cols])
            pks_str = ", ".join(pks if isinstance(pks, list) else [str(pks)])
            fks_str = ", ".join(
                [fk if isinstance(fk, str) else f"{fk.get('column','')}→{fk.get('ref_table','')}.{fk.get('ref_column','')}" for fk in (fks if isinstance(fks, list) else [])]
            )
            line = f"{t}: cols[{cols_str}]"
            if pks_str: line += f" | PK[{pks_str}]"
            if fks_str: line += f" | FK[{fks_str}]"
            buf.append(line)
        elif isinstance(data, dict):
            # flatten {table_name: {columns: [...], ...}}
            for t, meta in data.items():
                cols = meta.get("columns", [])
                pks = meta.get("pks") or meta.get("primary_keys") or []
                fks = meta.get("fks") or []
                cols_str = ", ".join([c if isinstance(c, str) else c.get("name", "") for c in cols])
                pks_str = ", ".join(pks if isinstance(pks, list) else [str(pks)])
                fks_str = ", ".join(
                    [fk if isinstance(fk, str) else f"{fk.get('column','')}→{fk.get('ref_table','')}.{fk.get('ref_column','')}" for fk in (fks if isinstance(fks, list) else [])]
                )
                line = f"{t}: cols[{cols_str}]"
                if pks_str: line += f" | PK[{pks_str}]"
                if fks_str: line += f" | FK[{fks_str}]"
                buf.append(line)
    return "\n".join(buf)


def _read_yaml(path: str) -> dict:
    try:
        import yaml
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        return {}
    return {}


def _render_data_model(work_dir: str) -> str:
    """
    Render target tables/columns from data_model.yaml (if present).
    Supports multiple shapes:
      - list of dicts: [{name|table|target: str, columns|cols|fields: [str|{name:...}]}]
      - list of strings: ["target_table", ...]
      - dict: {table_name: {columns|cols|fields: [...]}}
      - dict: {table_name: [col1, col2, ...]}
    """
    dm = _read_yaml(os.path.join(work_dir, "data_model.yaml"))
    if not dm:
        return ""

    lines = []

    def _norm_cols(cols):
        # cols can be list[str] or list[dict{name:...}] or None
        if cols is None:
            return []
        out = []
        for c in cols:
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, dict):
                # try common keys
                out.append(c.get("name") or c.get("column") or c.get("field") or "")
            else:
                out.append(str(c))
        return [c for c in out if c]

    if isinstance(dm, list):
        # items can be dicts OR plain strings
        for item in dm:
            if isinstance(item, dict):
                name = item.get("name") or item.get("table") or item.get("target") or item.get("id")
                cols = _norm_cols(item.get("columns") or item.get("cols") or item.get("fields"))
                if name:
                    if cols:
                        lines.append(f"[TARGET] {name}: {', '.join(cols)}")
                    else:
                        lines.append(f"[TARGET] {name}")
            elif isinstance(item, str):
                lines.append(f"[TARGET] {item}")
            else:
                # unknown shape; stringify safely
                lines.append(f"[TARGET] {str(item)}")

    elif isinstance(dm, dict):
        # values can be dicts OR lists (of columns)
        for name, meta in dm.items():
            if isinstance(meta, dict):
                cols = _norm_cols(meta.get("columns") or meta.get("cols") or meta.get("fields"))
                if cols:
                    lines.append(f"[TARGET] {name}: {', '.join(cols)}")
                else:
                    lines.append(f"[TARGET] {name}")
            elif isinstance(meta, list):
                cols = _norm_cols(meta)
                if cols:
                    lines.append(f"[TARGET] {name}: {', '.join(cols)}")
                else:
                    lines.append(f"[TARGET] {name}")
            else:
                # scalar or unknown → print table name only
                lines.append(f"[TARGET] {name}")

    else:
        # unexpected top-level shape: best-effort stringify
        lines.append("[TARGETS]\n" + json.dumps(dm, indent=2))

    return "\n".join(lines)



def _schema_string_from_workspace(work_dir: str) -> str:
    parts = []

    ws = _read_json_schemas(work_dir)
    if ws:
        parts.append("WORKSPACE SCHEMAS:")
        parts.append(ws)

    dm = _render_data_model(work_dir)
    if dm:
        parts.append("\nDATA MODEL (targets):")
        parts.append(dm)

    return "\n".join(parts).strip()


# ---------- snowflake schema summary ----------

def _schema_string_from_snowflake(creds_path: str, db_name: Optional[str], schema_name: Optional[str]) -> str:
    rows = fetch_tables(creds_path, database=db_name, schema=schema_name)
    by_table = {}
    for t, c, d in rows:
        by_table.setdefault(t, []).append(f"{c} ({d})")
    lines = []
    for t in sorted(by_table):
        cols = ", ".join(by_table[t])
        lines.append(f"{t}: {cols}")
    return "\n".join(lines)


# ---------- main SoT pipeline ----------

def sot_pipeline(
    question: str,
    creds_path: str,
    work_dir: str,
    db_name: Optional[str] = None,
    schema_name: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 1.0,
    retry: int = MAX_CRITIC_ATTEMPTS,
) -> Tuple[bool, str, str]:
    """
    SQL-of-Thought sequence using modular agent classes:
      1) SchemaLinkingAgent   -> corrected_schema
      2) SubproblemAgent      -> sub_json
      3) QueryPlanAgent       -> plan
      4) SQLAgent             -> sql
      5) execute + CorrectionSQLAgent loop -> corrected sql (<= MAX_CRITIC_ATTEMPTS)
    Returns: (ok, result_or_error, debug_log)
    """
    debug_lines: List[str] = []
    debug_lines.append(f"DB: {db_name}, SCHEMA_HINT: {schema_name}, MODEL: {model}, TEMP: {temperature}")
    debug_lines.append(f"WORK_DIR: {work_dir}")

    # 0) Build schema context = WORKSPACE + SNOWFLAKE
    ws_schema = _schema_string_from_workspace(work_dir)
    sf_schema = _schema_string_from_snowflake(creds_path, db_name, schema_name)
    schema_context = "\n\n".join(
        [s for s in [ws_schema, "SNOWFLAKE TABLES (active context):\n" + sf_schema if sf_schema else ""] if s]
    ).strip()

    debug_lines.append("=== SCHEMA_CONTEXT ===")
    debug_lines.append(schema_context if schema_context else "<EMPTY>")

    # Initialize LLM client wrapper
    llm_client = LLMClient(call_llm_func=call_llm)
    
    # Initialize agents
    schema_agent = SchemaLinkingAgent(llm_client)
    subproblem_agent = SubproblemAgent(llm_client)
    plan_agent = QueryPlanAgent(llm_client)
    sql_agent = SQLAgent(llm_client)
    correction_plan_agent = CorrectionPlanAgent(llm_client)
    correction_sql_agent = CorrectionSQLAgent(llm_client)

    # 1) Schema Linking Agent
    corrected_schema = schema_agent.link(question, schema_context, model=model, temperature=temperature)
    debug_lines.append("=== SCHEMA_AGENT_OUTPUT ===")
    debug_lines.append(corrected_schema)

    # 2) Subproblem Agent
    sub_json = subproblem_agent.decompose(question, corrected_schema, model=model, temperature=temperature)
    debug_lines.append("=== SUBPROBLEM_OUTPUT ===")
    debug_lines.append(json.dumps(sub_json, indent=2) if isinstance(sub_json, (dict, list)) else str(sub_json))

    # 3) Query Plan Agent
    plan = plan_agent.plan(question, corrected_schema, sub_json, model=model, temperature=temperature)
    debug_lines.append("=== PLAN_OUTPUT ===")
    debug_lines.append(plan)

    # 4) SQL Agent
    sql_raw = sql_agent.generate(question, plan, corrected_schema, model=model, temperature=temperature)
    sql = postprocess_sql(sql_raw)
    debug_lines.append("=== SQL_ATTEMPT_1 ===")
    debug_lines.append(sql)

    # 5) Execute + Correction Loop
    ok, out = run_sql(creds_path, sql, database=db_name, schema=schema_name)
    attempts = 0
    while (not ok) and attempts < retry:
        attempts += 1
        debug_lines.append(f"=== EXEC_ERROR_{attempts} ===")
        debug_lines.append(str(out))

        # Create correction plan
        correction_plan = correction_plan_agent.create_plan(
            question, sql, corrected_schema, database_error=str(out),
            model=model, temperature=temperature
        )
        debug_lines.append(f"=== CORRECTION_PLAN_OUTPUT_{attempts} ===")
        debug_lines.append(correction_plan)

        # Generate corrected SQL
        corrected_sql_raw = correction_sql_agent.generate(
            question, corrected_schema, correction_plan, sql,
            model=model, temperature=temperature
        )
        sql = postprocess_sql(corrected_sql_raw)
        debug_lines.append(f"=== SQL_ATTEMPT_{attempts+1} ===")
        debug_lines.append(sql)

        ok, out = run_sql(creds_path, sql, database=db_name, schema=schema_name)

    if ok:
        debug_lines.append("=== FINAL_SQL ===")
        debug_lines.append(sql)
        return True, sql, "\n".join(debug_lines)

    debug_lines.append("=== FINAL_ERROR ===")
    debug_lines.append(str(out))
    print("".join(debug_lines))
    return False, str(out), "\n".join(debug_lines)
