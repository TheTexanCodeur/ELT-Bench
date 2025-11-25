from typing import Optional, List

class SQLAgent:
    """SQL Agent - generates SQL queries from plans."""
    
    def __init__(self, llm_client, executor=None):
        """
        Args:
            llm_client: LLM client for generating SQL
            executor: Optional ActionExecutor for testing queries
        """
        self.llm = llm_client
        self.executor = executor
    
    def generate(self, question: str, plan: str, schema: str,
                 model: str = "gpt-4o", temperature: float = 1.0,
                 critic_issues: Optional[List[str]] = None) -> str:
        """
        Generate SQL query from plan.
        
        Args:
            question: Natural language question
            plan: Query plan from QueryPlanAgent
            schema: Schema info from SchemaLinkingAgent
            model: LLM model to use
            temperature: LLM temperature
            critic_issues: Optional list of previous errors to fix
            
        Returns:
            SQL query string (may need postprocessing)
        """
        from .. import prompts
        
        prompt = prompts.sql_agent_prompt(
            question, 
            plan, 
            schema=schema,
            critic_issues=critic_issues
        )
        return self.llm.complete(prompt, model=model, temperature=temperature)
