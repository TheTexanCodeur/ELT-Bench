from .models import LLMClient

class Generator:
    def __init__(self, llm: LLMClient):
        self.llm = llm
    def generate_sql(self, plan:str, catalog:str)->str:
        prompt = f"You are a SQL expert. Catalog:\n{catalog}\nPlan:\n{plan}\nWrite final Snowflake SQL to create the required target table(s) in AIRBYTE_SCHEMA."
        return self.llm.complete(prompt, temperature=0.1)
