from typing import List
from .models import LLMClient

class Planner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(self, subs:List[str])->str:
        prompt = "Create a stepwise SQL query plan that solves these sub-problems:\n" + "\n".join(f"- {s}" for s in subs)
        return self.llm.complete(prompt)
