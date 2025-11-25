from typing import List, Optional, Any
import json

class QueryPlanAgent:
    """Query Plan Agent - creates step-by-step SQL execution plan."""
    
    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM client for generating query plans
        """
        self.llm = llm_client

    def plan(self, question: str, schema_info: str, subproblem_json: Any,
             model: str = "gpt-4o", temperature: float = 1.0,
             critic_issues: Optional[List[str]] = None) -> str:
        """
        Generate a step-by-step query plan.
        
        Args:
            question: Natural language question
            schema_info: Schema links from SchemaLinkingAgent
            subproblem_json: Subproblems from SubproblemAgent
            model: LLM model to use
            temperature: LLM temperature
            critic_issues: Optional list of previous errors to avoid
            
        Returns:
            Query plan string
        """
        from .. import prompts
        
        # Convert subproblems to string if needed
        subprob_str = json.dumps(subproblem_json) if isinstance(subproblem_json, (dict, list)) else str(subproblem_json)
        
        prompt = prompts.query_plan_agent_prompt(
            question, 
            schema_info, 
            subproblem_json=subprob_str,
            critic_issues=critic_issues
        )
        return self.llm.complete(prompt, model=model, temperature=temperature)
