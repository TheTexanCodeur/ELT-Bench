from typing import List, Any
import json

class SubproblemAgent:
    """Subproblem Agent - decomposes questions into SQL subproblems."""
    
    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM client for decomposing questions
        """
        self.llm = llm_client

    def decompose(self, question: str, schema_info: str, model: str = "gpt-4o",
                  temperature: float = 1.0) -> Any:
        """
        Decompose question into subproblems.
        
        Args:
            question: Natural language question
            schema_info: Schema links from SchemaLinkingAgent
            model: LLM model to use
            temperature: LLM temperature
            
        Returns:
            JSON object with subproblems (dict or list)
        """
        from .. import prompts
        
        prompt = prompts.subproblem_agent_prompt(question, schema_info)
        response = self.llm.complete(prompt, model=model, temperature=temperature)
        
        # Try to parse JSON, fallback to raw string
        response = response.strip()
        try:
            return json.loads(response)
        except Exception:
            # Try to extract JSON from markdown blocks
            import re
            m = re.search(r'(\{.*\}|\[.*\])', response, flags=re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
        return response
