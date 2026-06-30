import logging
import time
import re
from typing import Tuple, Dict, Any, List
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

class SQLAgent:
    """
    Agent 3: SQL Agent
    Generates SQL based strictly on the provided schema context.
    """
    def build_prompt(self, query: str, schema_context: str, mapping_hints: str = "", error_feedback: str = "") -> str:
        mapping_hints_block = f"{mapping_hints}\n" if mapping_hints else ""
        error_block = f"\n# ❌ PREVIOUS EXECUTION ERROR:\nYour previous SQL query failed with this error: {error_feedback}\nCRITICAL: The validator is case-insensitive. If it rejected 'createddate', DO NOT try 'CreatedDate' or 'CREATEDDATE'. You MUST pick a completely DIFFERENT, valid column that actually exists in the schema (e.g. `podate`, `createddt`, `prdate`). DO NOT hallucinate columns!\n" if error_feedback else ""
        
        return f"""ROLE:
You are a strict SQL generation engine for ERP databases.

CRITICAL RULES:
1. Use ONLY tables and columns provided in schema context.
2. NEVER invent table names.
3. Use strictly the EXACT table and column names from the provided schema. Check pluralization carefully.
4. Join tables exactly as specified in the Relationships section. Do not guess joins.
5. For date filtering, ALWAYS prefer the specific business date column (like `podate`, `prdate`) over audit columns (like `createddt`) unless specifically asked for creation date.
6. NEVER query `_attachment` or file metadata tables to calculate business totals. Always prefer `_header` or `_detail` tables for transactional data.
7. NEVER invent or hallucinate generic ERP column names.
8. NEVER use `CreatedDate`, `Amount`, or `TotalAmount` unless they explicitly exist in the schema context.
9. ONLY use columns from the provided schema context. If the requested data requires tables/columns that are NOT in the schema context, output exactly "SCHEMA_ERROR".
10. ALWAYS use fully qualified column names (e.g., `table_name`.`column_name`) and wrap them in backticks.
11. NEVER use `NOT IN` with a subquery unless you explicitly filter out NULL values in the subquery.
12. When filtering by boolean flags (e.g. `isactive`), ALWAYS handle potential NULLs if checking for falsy values.
13. Review the Mapping Hints (if any) carefully to map business terms (e.g. "total spend", "cycle time") to actual table and column names found in the schema context.
14. To calculate "Cycle Time", "Approval Time", or delays, use DATEDIFF or similar date functions on the relevant start and end date columns found in the schema context.
15. If a specific master table (e.g., for suppliers, vendors, items) is NOT provided in the schema context, DO NOT invent one and DO NOT join unrelated tables (like currency or config tables) just because they share a partial name. Instead, simply group by or return the ID column (e.g., `supplierid`, `itemid`) directly from the transactional table.
16. ABSOLUTELY DO NOT ADD ANY `WHERE isactive = 1`, `WHERE issubmitted = 1`, or ANY boolean flag filters! YOU MUST OMIT THEM! If you guess a flag that doesn't exist, you will crash the system! Only filter by dates or foreign keys!

OUTPUT:
Return only SQL query. No markdown formatting, no explanations, no `sql` tags.

---

[TABLE SCHEMA CONTEXT]
{schema_context}

{mapping_hints_block}{error_block}User Query: {query}
"""

    async def generate_sql(self, query: str, schema_context: str, mapping_hints: str = "", error_feedback: str = "") -> str:
        prompt = self.build_prompt(query, schema_context, mapping_hints, error_feedback)
        llm_start = time.time()
        temp = 0.6 if error_feedback else 0.0
        sql_query = await llm_service.generate(prompt=prompt, system="Output ONLY raw SQL.", temperature=temp)
        logger.info(f"PERF | SQL Gen LLM: {time.time() - llm_start:.3f}s")
        
        # Clean up code blocks
        clean_sql = re.sub(r'```(?:sql)?', '', sql_query, flags=re.IGNORECASE).replace('```', '').strip()
        print(f"GENERATED SQL: {clean_sql}")
        return clean_sql

    async def execute_sql(self, host, port, user, password, db_name, sql_query) -> str:
        import aiomysql
        try:
            kwargs = dict(host=host, port=port, user=user, password=password)
            if db_name:
                kwargs['db'] = db_name
            pool = await aiomysql.create_pool(**kwargs)
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if "LIMIT" not in sql_query.upper():
                        sql_query = sql_query.rstrip(";") + " LIMIT 50;"
                        
                    await cur.execute(sql_query)
                    rows = await cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    
                    res = []
                    res.append("| " + " | ".join(columns) + " |")
                    res.append("|" + "|".join(["---"] * len(columns)) + "|")
                    for row in rows:
                        clean_row = []
                        for val in row:
                            if isinstance(val, bytes):
                                if len(val) == 1:
                                    val = "Active" if val == b'\x01' else ("Inactive" if val == b'\x00' else val.hex())
                                else:
                                    try:
                                        val = val.decode('utf-8', errors='ignore')
                                    except Exception:
                                        val = val.hex()
                            clean_row.append(str(val).replace('\n', ' ').replace('|', '\\|') if val is not None else "NULL")
                        res.append("| " + " | ".join(clean_row) + " |")
            pool.close()
            await pool.wait_closed()
            return "\n".join(res)
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return f"Error executing query: {e}"

    async def execute_sql_raw(self, host, port, user, password, db_name, sql_query) -> list:
        import aiomysql
        try:
            kwargs = dict(host=host, port=port, user=user, password=password)
            if db_name:
                kwargs['db'] = db_name
            pool = await aiomysql.create_pool(**kwargs)
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    if "LIMIT" not in sql_query.upper():
                        sql_query = sql_query.rstrip(";") + " LIMIT 50;"
                        
                    await cur.execute(sql_query)
                    rows = await cur.fetchall()
            pool.close()
            await pool.wait_closed()
            return rows
        except Exception as e:
            logger.error(f"SQL raw execution error: {e}")
            raise e

sql_agent = SQLAgent()
