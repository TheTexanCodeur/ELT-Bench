from typing import Tuple, Optional, List
import json
import re

from . import prompts
from .llm import call_llm
from .snowflake_exec import run_sql, fetch_tables

MAX_CRITIC_ATTEMPTS = 3


# ---------- minimal SoT-compatible helpers ----------

def clean_json(s: str):
    """
    Try to parse a JSON object/list out of an LLM response.
    Falls back to a best-effort extraction of the first {...} or [...] block.
    """
    s = s.strip()
    # quick path
    try:
        return json.loads(s)
    except Exception:
        pass
    # try to extract the first balanced JSON object/array
    m = re.search(r'(\{.*\}|\[.*\])', s, flags=re.DOTALL)
    if m:
        frag = m.group(1)
        try:
            return json.loads(frag)
        except Exception:
            pass
    # last resort: return raw string
    return s


def postprocess_sql(sql: str) -> str:
    """
    Normalize the SQL emitted by LLMs:
    - strip code fences/backticks,
    - remove trailing semicolons and whitespace,
    - collapse multiple spaces/newlines.
    """
    if sql is None:
        return ""
    s = sql.strip()
    # remove markdown fences
    s = re.sub(r"^```(?:sql)?\s*|\s*```$", "", s, flags=re.IGNORECASE | re.DOTALL).strip()
    # remove leading "SQL:" or similar
    s = re.sub(r"^\s*(SQL\s*:\s*)", "", s, flags=re.IGNORECASE).strip()
    # truncate after first semicolon if multiple are present (common extra commentary)
    # but keep CTEs etc.—so only trim a FINAL trailing semicolon
    s = s.rstrip("; \n\t\r")
    return s


# ---------- schema formatting ----------

def _schema_string(creds_path: str, db_name: Optional[str], schema_name: Optional[str]) -> str:
    """
    Build a compact schema summary string (table: col (type), col (type) ...)
    from the active Snowflake database/schema.
    """
    rows = fetch_tables(creds_path, database=db_name, schema=schema_name)
    by_table = {}
    for t, c, d in rows:
        by_table.setdefault(t, []).append(f"{c} ({d})")
    lines = []
    for t in sorted(by_table):
        cols = ", ".join(by_table[t])
        lines.append(f"{t}: {cols}")
    return "\n".join(lines)


# ---------- main SoT pipeline (faithful to your evaluate() script) ----------

def sot_pipeline(
    question: str,
    creds_path: str,
    db_name: Optional[str] = None,
    schema_name: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 1.0,
    retry: int = MAX_CRITIC_ATTEMPTS,   # keep parity with SoT's MAX_CRITIC_ATTEMPTS
) -> Tuple[bool, str, str]:
    """
    SQL-of-Thought sequence (mirrors your 'evaluate()' flow):
      1) alt_schema_linking_agent_prompt   -> corrected_schema
      2) subproblem_agent_prompt           -> sub_json
      3) query_plan_agent_prompt           -> plan
      4) sql_agent_prompt                  -> sql
      5) execute + correction loop (plan -> corrected sql) up to MAX_CRITIC_ATTEMPTS

    Returns: (ok, result_or_error, debug_log)
    """
    debug_lines: List[str] = []
    debug_lines.append(f"DB: {db_name}, SCHEMA_HINT: {schema_name}, MODEL: {model}, TEMP: {temperature}")

    # 0) Discover schema text
    schema_list = _schema_string(creds_path, db_name, schema_name)
    debug_lines.append("=== SCHEMA_DISCOVERED ===")
    debug_lines.append(schema_list or "<EMPTY SCHEMA>")
    print(schema_list)

    # 1) Schema Agent (SoT uses alt_schema_linking_agent_prompt directly)
    schema_prompt = prompts.alt_schema_linking_agent_prompt(question, schema_list)
    corrected_schema = call_llm(schema_prompt, model=model, temperature=temperature)
    debug_lines.append("=== SCHEMA_AGENT_PROMPT ===")
    debug_lines.append(schema_prompt)
    print("=== SCHEMA_AGENT_PROMPT ===")
    debug_lines.append("=== SCHEMA_AGENT_OUTPUT ===")
    debug_lines.append(corrected_schema)
    print(corrected_schema)

    # 2) Subproblem Agent
    subproblem_prompt = prompts.subproblem_agent_prompt(question, corrected_schema)
    sub_json_raw = call_llm(subproblem_prompt, model=model, temperature=temperature)
    sub_json = clean_json(sub_json_raw)
    debug_lines.append("=== SUBPROBLEM_PROMPT ===")
    debug_lines.append(subproblem_prompt)
    debug_lines.append("=== SUBPROBLEM_OUTPUT ===")
    debug_lines.append(json.dumps(sub_json, indent=2) if isinstance(sub_json, (dict, list)) else str(sub_json))

    # 3) Query Plan Agent
    plan_prompt = prompts.query_plan_agent_prompt(question, corrected_schema, subproblem_json=json.dumps(sub_json) if isinstance(sub_json, (dict, list)) else str(sub_json))
    plan = call_llm(plan_prompt, model=model, temperature=temperature)
    debug_lines.append("=== PLAN_PROMPT ===")
    debug_lines.append(plan_prompt)
    debug_lines.append("=== PLAN_OUTPUT ===")
    debug_lines.append(plan)

    # 4) SQL Generating Agent
    sql_prompt = prompts.sql_agent_prompt(question, plan, corrected_schema)
    sql = call_llm(sql_prompt, model=model, temperature=temperature)
    sql = postprocess_sql(sql)
    debug_lines.append("=== SQL_PROMPT_1 ===")
    debug_lines.append(sql_prompt)
    debug_lines.append("=== SQL_ATTEMPT_1 ===")
    debug_lines.append(sql)

    # 5) Execute + Correction Loop (up to MAX_CRITIC_ATTEMPTS)
    ok, out = run_sql(creds_path, sql, database=db_name, schema=schema_name)
    attempts = 0
    while (not ok) and attempts < retry:
        attempts += 1
        debug_lines.append(f"=== EXEC_ERROR_{attempts} ===")
        debug_lines.append(str(out))

        correction_plan_prompt = prompts.correction_plan_agent_prompt(question, sql, corrected_schema, out)
        correction_plan = call_llm(correction_plan_prompt, model=model, temperature=temperature)
        debug_lines.append(f"=== CORRECTION_PLAN_PROMPT_{attempts} ===")
        debug_lines.append(correction_plan_prompt)
        debug_lines.append(f"=== CORRECTION_PLAN_OUTPUT_{attempts} ===")
        debug_lines.append(correction_plan)

        correction_sql_prompt = prompts.correction_sql_agent_prompt(question, corrected_schema, correction_plan, sql)
        corrected_sql = call_llm(correction_sql_prompt, model=model, temperature=temperature)
        sql = postprocess_sql(corrected_sql)
        debug_lines.append(f"=== SQL_CORRECTION_PROMPT_{attempts} ===")
        debug_lines.append(correction_sql_prompt)
        debug_lines.append(f"=== SQL_ATTEMPT_{attempts+1} ===")
        debug_lines.append(sql)

        ok, out = run_sql(creds_path, sql, database=db_name, schema=schema_name)

    if ok:
        debug_lines.append("=== FINAL_SQL ===")
        debug_lines.append(sql)
        return True, sql, "\n".join(debug_lines)

    debug_lines.append("=== FINAL_ERROR ===")
    debug_lines.append(str(out))
    return False, str(out), "\n".join(debug_lines)
