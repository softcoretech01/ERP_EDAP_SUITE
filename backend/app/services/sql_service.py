from ..ai.ollama_service import ollama_service
from ..db.connection_manager import connection_manager
import json
import re
from sqlalchemy import text

class SQLService:
    def validate_sql(self, sql: str) -> bool:
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith("SELECT"):
            return False
            
        forbidden = ["DELETE", "UPDATE", "DROP", "TRUNCATE", "INSERT", "ALTER", "CREATE", "GRANT", "REVOKE"]
        for word in forbidden:
            if re.search(rf"\b{word}\b", sql_upper):
                return False
        return True

    def validate_sql_against_schema(self, sql: str, schema_catalog: dict) -> bool:
        if not self.validate_sql(sql):
            return False
            
        # Clean sql for parsing
        clean_sql = re.sub(r'[`"\[\]]', '', sql)
        clean_sql = re.sub(r'\s+', ' ', clean_sql)
        
        # Find tables after FROM or JOIN
        matches = re.findall(r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)', clean_sql, re.IGNORECASE)
        
        sql_keywords = {"SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TABLE", "VIEW", "INDEX", "LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL", "WHERE", "ON"}
        for table in matches:
            if table.upper() in sql_keywords:
                continue
            if table not in schema_catalog:
                return False
        return True

    async def generate_sql(self, query: str, schema_catalog: dict) -> str:
        schema_str = json.dumps(schema_catalog, indent=2)
        system_prompt = f"""
        You are a SQL generator for an ERP system. 
        You MUST follow these rules strictly:
        - Use ONLY the tables and columns defined in the schema below.
        - Never invent or use tables or columns that do not exist in the schema.
        - ONLY SELECT statements are allowed. Do not use INSERT, UPDATE, DELETE, ALTER, etc.
        - For any query retrieving lists of records, you MUST enforce a LIMIT (maximum 100 rows).
        - If the required tables for the user's intent are completely missing from the schema context, you MUST stop and output EXACTLY the phrase: "I don't have enough schema information".
        - Return ONLY the raw SQL query, no explanation, no markdown formatting (do not wrap in backticks or markdown code blocks).
        
        Schema:
        {schema_str}
        """
        
        sql = await ollama_service.generate(
            prompt=f"Generate SQL for this query: '{query}'\nSQL:",
            system=system_prompt,
            temperature=0.0,
            num_predict=256
        )
        
        # Clean and extract the SQL block robustly
        sql_clean = sql.strip()

        # Remove any leading label like "SQL:" if present
        if sql_clean.upper().startswith('SQL:'):
            sql_clean = sql_clean[4:].strip()

        # 1. Check for ```sql ... ``` markdown blocks
        match = re.search(r"```sql\s*(.*?)\s*```", sql_clean, re.DOTALL | re.IGNORECASE)
        if match:
            sql_clean = match.group(1).strip()
        else:
            # 2. Check for general ``` ... ``` code blocks
            match = re.search(r"```\s*(.*?)\s*```", sql_clean, re.DOTALL | re.IGNORECASE)
            if match:
                sql_clean = match.group(1).strip()
            else:
                # 3. Look for SELECT ... ; inline structure
                match = re.search(r"\bSELECT\b.*?;", sql_clean, re.DOTALL | re.IGNORECASE)
                if match:
                    sql_clean = match.group(0).strip()
        # Ensure only one occurrence of the query
        sql_clean = sql_clean.split('\n')[0].strip()

        # Enforce LIMIT if missing
        sql_upper = sql_clean.upper()
        if "LIMIT" not in sql_upper and not any(kw in sql_upper for kw in ["COUNT(", "SUM(", "AVG(", "MIN(", "MAX("]):
            sql_clean = sql_clean.rstrip(';')
            sql_clean = f"{sql_clean} LIMIT 100"

        return sql_clean

    async def execute_query(self, sql: str, db_conn_id: int, host: str, port: int, user: str, encrypted_password: str, db_name: str, schema_catalog: dict = None):
        if "I don't have enough schema information" in sql:
            raise ValueError("I don't have enough schema information to answer your query. Please rephrase or ensure the required tables exist in the database.")
            
        if schema_catalog is not None:
            if not self.validate_sql_against_schema(sql, schema_catalog):
                raise ValueError("Invalid SQL query generated. The query references tables outside the database schema.")
        else:
            if not self.validate_sql(sql):
                raise ValueError("Invalid SQL query generated. Only SELECT operations are allowed.")
            
        session_maker = connection_manager.get_session_maker(db_conn_id, host, port, user, encrypted_password, db_name)
        try:
            async with session_maker() as session:
                result = await session.execute(text(sql))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return rows
        except Exception as e:
            raise ValueError(f"Database query failed. Error: {str(e)}\n\nGenerated SQL:\n{sql}")

sql_service = SQLService()

