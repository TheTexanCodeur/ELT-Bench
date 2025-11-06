from typing import Dict, Any, List, Optional
import json, os, textwrap

class SchemaLinkingAgent:
    """Schema Linking Agent - identifies relevant tables and columns for a question."""
    
    def __init__(self, llm_client, executor=None):
        """
        Args:
            llm_client: LLM client for generating schema links
            executor: Optional ActionExecutor for dynamic schema exploration
        """
        self.llm = llm_client
        self.executor = executor
    
    def link(self, question: str, schema_context: str, model: str = "gpt-4o", 
             temperature: float = 1.0) -> str:
        """
        Generate schema links for the question.
        
        Args:
            question: Natural language question
            schema_context: Available schema information
            model: LLM model to use
            temperature: LLM temperature
            
        Returns:
            String with the prompt used
            String with relevant table and column links
        """
        from .. import prompts
        
        prompt = prompts.alt_schema_linking_agent_prompt(question, schema_context)
        return prompt , self.llm.complete(prompt, model=model, temperature=temperature)
