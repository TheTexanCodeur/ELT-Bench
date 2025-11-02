from typing import Optional


class CorrectionPlanAgent:
    """Correction Plan Agent - analyzes errors and creates correction plans."""
    
    def __init__(self, llm_client, executor=None):
        """
        Args:
            llm_client: LLM client for generating correction plans
            executor: Optional ActionExecutor for testing fixes
        """
        self.llm = llm_client
        self.executor = executor
    
    def create_plan(self, question: str, wrong_sql: str, schema: str,
                    database_error: Optional[str] = None,
                    model: str = "gpt-4o", temperature: float = 1.0) -> str:
        """
        Analyze error and create correction plan.
        
        Args:
            question: Original question
            wrong_sql: Failed SQL query
            schema: Schema info
            database_error: Optional database error message
            model: LLM model to use
            temperature: LLM temperature
            
        Returns:
            Correction plan string
        """
        from .. import prompts
        
        prompt = prompts.correction_plan_agent_prompt(
            question, 
            wrong_sql, 
            schema,
            database_error=database_error
        )
        return self.llm.complete(prompt, model=model, temperature=temperature)
