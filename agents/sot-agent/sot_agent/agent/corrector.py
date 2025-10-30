import snowflake.connector, time, re
from typing import Tuple

ERROR_BUDGET = 5

def execute_sql_and_return_error(conn_params:dict, sql:str)->Tuple[bool,str]:
    try:
        conn = snowflake.connector.connect(**conn_params)
        cur = conn.cursor()
        for stmt in [s for s in re.split(r";\s*\n?", sql) if s.strip()]:
            cur.execute(stmt)
        return True, ""
    except Exception as e:
        return False, str(e)
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

class Corrector:
    def __init__(self, llm):
        self.llm = llm

    def repair(self, sql:str, error:str, catalog:str)->str:
        prompt = f"The following Snowflake SQL errored. Error:\n{error}\nCatalog:\n{catalog}\nProvide a corrected SQL."
        return self.llm.complete(prompt, temperature=0.2)

    def guided_loop(self, conn_params:dict, sql:str, catalog:str)->Tuple[bool,str]:
        ok, err = execute_sql_and_return_error(conn_params, sql)
        tries = 0
        while not ok and tries < ERROR_BUDGET:
            sql = self.repair(sql, err, catalog)
            ok, err = execute_sql_and_return_error(conn_params, sql)
            tries += 1
        return ok, sql if ok else err
