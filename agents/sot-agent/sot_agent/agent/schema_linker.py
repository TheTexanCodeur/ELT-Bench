from typing import Dict, Any, List
import json, os, textwrap

class SchemaLinker:
    def __init__(self, snowflake_catalog_fetcher):
        self._fetch = snowflake_catalog_fetcher

    def link(self, db_name:str, schema:str)->Dict[str, Any]:
        """Return a lightweight catalog and FK guesses suitable for SoT."""
        return self._fetch(db_name, schema)
