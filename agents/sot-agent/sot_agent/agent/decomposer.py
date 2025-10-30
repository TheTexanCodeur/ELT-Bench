from typing import List
from .models import LLMClient

class Decomposer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def subproblems(self, instruction:str, catalog:str)->List[str]:
        prompt = f"Given this warehouse catalog:\n{catalog}\nInstruction:\n{instruction}\nBreak into atomic sub-problems."
        return [s.strip("- ").strip() for s in self.llm.complete(prompt).split("\n") if s.strip()]
