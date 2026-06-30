import logging
from typing import Dict, Any, List
from ..services.sql_validator import sql_validator

logger = logging.getLogger(__name__)

class SQLValidatorAgent:
    """
    Agent 4: SQL Validator Agent
    Uses AST parsing to guarantee no hallucinations or unsafe SQL make it to the database.
    """
    
    def parse_schema_context(self, schema_context_str: str) -> List[Dict[str, Any]]:
        import re
        tables_in_context = []
        current_table = None
        for line in schema_context_str.split("\n"):
            line = line.strip()
            table_match = re.match(r'^\d+\.\s+`(?:[^`]+)`\s*\.\s*`([^`]+)`', line)
            if table_match:
                current_table = table_match.group(1)
                tables_in_context.append({"table_name": current_table, "columns": []})
            elif not table_match:
                table_match_no_db = re.match(r'^\d+\.\s+`([^`]+)`', line)
                if table_match_no_db:
                    current_table = table_match_no_db.group(1)
                    tables_in_context.append({"table_name": current_table, "columns": []})
                elif line.startswith("Columns:") and current_table:
                    cols_str = line.replace("Columns:", "").strip()
                    cols = [c.strip() for c in cols_str.split(",")]
                    tables_in_context[-1]["columns"].extend(cols)
                elif line.endswith("Columns:") and not line.startswith("Columns:"):
                    current_table = line.split(" Columns:")[0].replace("`", "").strip()
                    tables_in_context.append({"table_name": current_table, "columns": []})
                elif line.startswith("- ") and current_table and tables_in_context[-1]["columns"] == []:
                    col_name_part = line.split("(")[0]
                    clean_col = re.sub(r'\[.*?\]', '', col_name_part).replace('-', '').strip()
                    tables_in_context[-1]["columns"].append(clean_col)
        return tables_in_context

    async def validate(self, sql: str, schema_context_tables: List[Dict[str, Any]]) -> str:
        if "I don't have enough schema information" in sql:
            return "Error: Could not determine enough schema information to answer."
            
        is_valid, msg = await sql_validator.validate_sql_against_schema(sql, schema_context_tables)
        if not is_valid:
            logger.error(f"SQL Validation Failed: {msg}\nQuery: {sql}")
            return f"Error: SQL Validation Failed. {msg}"
            
        logger.info("SQL Validated successfully via AST parser.")
        return msg

sql_validator_agent = SQLValidatorAgent()
