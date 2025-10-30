import os
from typing import Optional

class LLMClient:
    """Thin abstraction over provider-specific clients; extend as needed."""
    def __init__(self, model:str):
        self.model = model
        # Defer provider init until call; avoid importing heavy SDKs at import-time.

    def complete(self, prompt:str, system:Optional[str]=None, temperature:float=0.2, max_tokens:int=2048)->str:
        """Return a string completion using whichever provider the model implies."""
        # Minimal provider routing by model name prefix
        if self.model.startswith("gpt-"):
            from openai import OpenAI
            client = OpenAI()
            msgs = []
            if system:
                msgs.append({"role":"system","content":system})
            msgs.append({"role":"user","content":prompt})
            resp = client.chat.completions.create(model=self.model, messages=msgs, temperature=temperature, max_tokens=max_tokens)
            return resp.choices[0].message.content
        elif self.model.startswith("claude-"):
            import anthropic
            client = anthropic.Anthropic()
            msgs = []
            if system:
                msgs.append({"role":"system","content":system})
            # Anthropics messages are a bit different; keep simple:
            message = client.messages.create(model=self.model, max_tokens=max_tokens, temperature=temperature, system=system or "", messages=[{"role":"user","content":prompt}])
            return "".join([b.text for b in message.content if getattr(b, "type", "")=="text"])
        elif self.model.startswith("accounts/fireworks/models/"):
            from fireworks.client import Fireworks
            fw = Fireworks()
            # Rough parity via chat completions if supported
            resp = fw.chat.completions.create(model=self.model, messages=[{"role":"user","content":prompt}], temperature=temperature, max_tokens=max_tokens)
            return resp.choices[0].message.content
        else:
            raise ValueError(f"Unknown or unsupported model: {self.model}")
