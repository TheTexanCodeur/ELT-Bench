import os
from typing import Optional, Callable

class LLMClient:
    """
    Thin abstraction over LLM calls.
    Can use either provider-specific clients OR a custom call_llm function.
    """
    def __init__(self, model: Optional[str] = None, call_llm_func: Optional[Callable] = None):
        """
        Args:
            model: Model name (for provider-specific routing)
            call_llm_func: Custom LLM calling function (signature: call_llm(prompt, model, temperature) -> str)
        """
        self.model = model
        self.call_llm_func = call_llm_func

    def complete(self, prompt: str, system: Optional[str] = None, 
                 temperature: float = 0.2, max_tokens: int = 2048,
                 model: Optional[str] = None) -> str:
        """
        Return a string completion.
        
        Args:
            prompt: The prompt string
            system: Optional system message (not used if call_llm_func provided)
            temperature: LLM temperature
            max_tokens: Max tokens to generate
            model: Model name (overrides self.model)
            
        Returns:
            String completion
        """
        # If custom call_llm function provided, use it
        if self.call_llm_func:
            return self.call_llm_func(prompt, model=model or self.model, temperature=temperature)
        
        # Otherwise fall back to provider-specific routing
        model_to_use = model or self.model
        if not model_to_use:
            raise ValueError("Must provide either model or call_llm_func")
            
        # Minimal provider routing by model name prefix
        if model_to_use.startswith("gpt-"):
            from openai import OpenAI
            client = OpenAI()
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=model_to_use, 
                messages=msgs, 
                temperature=temperature, 
                max_tokens=max_tokens
            )
            return resp.choices[0].message.content
            
        elif model_to_use.startswith("claude-"):
            import anthropic
            client = anthropic.Anthropic()
            message = client.messages.create(
                model=model_to_use, 
                max_tokens=max_tokens, 
                temperature=temperature, 
                system=system or "", 
                messages=[{"role": "user", "content": prompt}]
            )
            return "".join([b.text for b in message.content if getattr(b, "type", "") == "text"])
            
        else:
            raise ValueError(f"Unknown or unsupported model: {model_to_use}")
