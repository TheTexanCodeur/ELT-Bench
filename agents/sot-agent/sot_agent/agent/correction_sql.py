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

class CorrectionSQLAgent:
    """Correction SQL Agent - generates corrected SQL based on correction plan."""
    
    def __init__(self, llm_client, executor=None):
        """
        Args:
            llm_client: LLM client for generating corrected SQL
            executor: Optional ActionExecutor for testing fixes
        """
        self.llm = llm_client
        self.executor = executor
    
    def generate(self, question: str, schema: str, 
                 correction_plan: str, wrong_sql: str,
                 model: str = "gpt-4o", temperature: float = 1.0) -> str:
        """
        Generate corrected SQL based on correction plan.
        
        Args:
            question: Original question
            schema: Schema info
            correction_plan: Plan from create_correction_plan()
            wrong_sql: Failed SQL query
            model: LLM model to use
            temperature: LLM temperature
            
        Returns:
            Corrected SQL query string
        """
        from .. import prompts
        
        prompt = prompts.correction_sql_agent_prompt(
            question, 
            schema, 
            correction_plan, 
            wrong_sql
        )
        return self.llm.complete(prompt, model=model, temperature=temperature)

    def guided_loop(self, conn_params:dict, sql:str, catalog:str)->Tuple[bool,str]:
        ok, err = execute_sql_and_return_error(conn_params, sql)
        tries = 0
        while not ok and tries < ERROR_BUDGET:
            sql = self.repair(sql, err, catalog)
            ok, err = execute_sql_and_return_error(conn_params, sql)
            tries += 1
        return ok, sql if ok else err
