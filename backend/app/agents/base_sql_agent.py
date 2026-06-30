import logging
import time
import aiomysql # IDE trigger
import re
from ..core.tenant_manager import tenant_manager
from ..core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.llm_service import llm_service
from ..services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

class BaseSQLAgent:
    def __init__(self):
        self.MODULE_NAME = None
        self.GLOBAL_INSTRUCTIONS = ""
        
    async def _execute_sql(self, host, port, user, password, db_name, sql_query) -> str:
        try:
            kwargs = dict(host=host, port=port, user=user, password=password)
            if db_name:
                kwargs['db'] = db_name
            pool = await aiomysql.create_pool(**kwargs)
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Enforce safety
                    import re
                    # Strip out all single-line and multi-line comments for validation
                    clean_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
                    clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)
                    upper_query = clean_query.strip().upper()
                    
                    # Remove leading parenthesis if any
                    while upper_query.startswith("("):
                        upper_query = upper_query[1:].strip()
                        
                    first_word = upper_query.split()[0] if upper_query.split() else ""
                    if first_word not in ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN"):
                        with open("d:\\ERP Assitant\\backend\\debug.log", "a") as f:
                            f.write(f"SAFETY ERROR: Received '{first_word}'. RAW QUERY: {sql_query}\n---\n")
                        return f"Error: Only SELECT or WITH queries are allowed. Received: {first_word}"
                    
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
            logger.error(f"BaseSQLAgent execution error: {e}")
            with open("d:\\ERP Assitant\\backend\\debug.log", "a") as f:
                f.write(f"EXECUTION ERROR: {e}\nQUERY: {sql_query}\n---\n")
            return f"Error executing query: {e}"

    def build_prompt(self, query: str, schema_text: str) -> str:
        return f"""You are a DATABASE-SAFE SQL ASSISTANT.

Your job is to convert user questions into SQL queries ONLY using the provided database schema context.

---

# 🚨 CRITICAL RULES (NON-NEGOTIABLE)

1. NEVER hallucinate or assume:
   - table names
   - column names
   - relationships
   - data values

2. ONLY use schema provided in the `[TABLE SCHEMA CONTEXT]`.
   If a table/column is not in the schema context → DO NOT use it.
   NEVER use a column name just because it is mentioned as an example or synonym in the Global Instructions. You must find the EXACT matching column inside the schema context!

3. Do NOT try to "guess" missing schema. If the exact requested column is missing, use the closest available column FROM THE CONTEXT or omit it.
   If the required TABLE for the user's intent is completely missing from the schema context, you MUST stop and output EXACTLY the phrase: "I don't have enough schema information". Do not generate a fake SQL query.

4. ALWAYS generate a valid SQL query using the provided tables. You MUST use the FULL table name exactly as provided in the schema context (e.g. `database_name`.`table_name`). Never omit the database prefix.

5. ALWAYS wrap EVERY table name and column name in backticks (e.g. `database`.`table`, `Column Name`) inside the SQL query, because many names have spaces or reserved keywords.

---

# 📘 ERP HEADER-DETAIL ARCHITECTURE & BUSINESS RULES

Most ERP modules contain two types of tables:
1. Header Table (Stores master transaction info: document number, date, status, customer/vendor)
2. Detail Table (Stores line-item details: items, quantity, rate, amount)

HEADER-DETAIL RELATIONSHIP RULES:
1. Every Header table is connected to Detail table.
2. Join must use configured primary key and foreign key.
3. Never guess joins. Use only configured relationships.

STANDARD JOIN PATTERN:
HeaderTable.PrimaryKey = DetailTable.ForeignKey

Examples:
- Purchase Requisition: tbl_PurchaseRequisition_Header.ID = tbl_PurchaseRequisition_Detail.ID
- Purchase Order: tbl_PurchaseOrder_Header.ID = tbl_PurchaseOrder_Detail.ID
- Sales Order: tbl_SalesOrder_Header.ID = tbl_SalesOrder_Detail.ID
- Invoice: tbl_Invoice_Header.ID = tbl_Invoice_Detail.ID

QUERY RULES:
- If user asks summary information (e.g., PR list, Purchase order status, Sales order status): Use Header table only.
- If user asks item details (e.g., PR item details, Purchase order items, Invoice item list): Join Header + Detail.
- "Created this month / today" = Filter by date columns (e.g., `created_at`, `date`, `PRDate`).
- "Open / Pending" = Filter by status indicating it is not closed.
- "Total value" = Use SUM(amount) or SUM(Quantity * Rate).

---

{self.GLOBAL_INSTRUCTIONS}

# ⚡ OUTPUT RULE

You MUST return ONLY valid SQL query OR a schema error message.

No explanations unless explicitly asked.

---

# ⚡ PERFORMANCE RULES

- Do NOT repeat reasoning steps
- Do NOT generate multiple query versions
- Produce ONE optimized SQL query only

---

# 🧠 SCHEMA USAGE RULE

You will always receive schema in this format:

[TABLE SCHEMA CONTEXT]
{{schema_text}}

Use ONLY these tables and columns.

---

# 🚫 FORBIDDEN BEHAVIOR

- Inventing columns (example: CylinderName if not present)
- Inventing relationships
- Using external knowledge
- Making assumptions about business logic

---

# ✅ SAFE BEHAVIOR

- Use only provided schema
- Validate column existence before using
- Prefer simplest query possible
- Avoid joins unless schema explicitly supports them

---

# ⚡ SQL GENERATION FORMAT

You must output your reasoning steps first, followed by the generated SQL wrapped in a code block:

1. User Intent
2. Selected Module
3. Selected Table
4. Selected Columns
5. SQL Validation Status
6. Generated SQL:
```sql
<query>
```

User Request: {query}
Context: {schema_text}
"""

    async def handle_query(self, db: AsyncSession, tenant_id: int, query: str, context: str, target_agents: list = None) -> str:
        total_start = time.time()
        connections = await tenant_manager.get_tenant_connections(db, tenant_id)
        if not connections:
            return "Error: No active database connection found for this workspace."
        connection_record = connections[0]

        from cryptography.fernet import Fernet
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(connection_record.encrypted_password.encode()).decode()

        # Determine module name from agents
        module_name = None
        if target_agents:
            # Check in reverse priority or just exact matches
            if "purchase_agent" in target_agents: module_name = "Purchase"
            elif "sales_agent" in target_agents: module_name = "Sales"
            elif "inventory_agent" in target_agents: module_name = "Inventory"
            elif "finance_agent" in target_agents: module_name = "Finance"
            elif "hr_agent" in target_agents: module_name = "HR"

        # 1. Fetch ONLY top 20 relevant schemas from Qdrant using module filter (NO full schema scan)
        qdrant_start = time.time()
        try:
            from qdrant_client.models import FieldCondition, MatchValue
            extra_conditions = []
            if module_name:
                extra_conditions.append(FieldCondition(key="business_domain", match=MatchValue(value=module_name.lower())))
                
            results = qdrant_service.search_vectors("schema_collection", tenant_id, query, limit=20, extra_conditions=extra_conditions)
            if not results:
                logger.warning(f"SQLAgent: No relevant schemas found in Qdrant for module {module_name}.")
                return f"Error: Could not retrieve any schema metadata for this query in the {module_name or 'selected'} module."
                
            # Build compact schema text for LLM prompt
            import json
            schema_summaries = []
            available_tables = []
            
            for r in results:
                json_str = r.get("json_schema", "")
                if json_str:
                    try:
                        schema_obj = json.loads(json_str)
                        db_str = schema_obj.get("database", "")
                        tbl = schema_obj.get("table", "")
                        cols = ", ".join(schema_obj.get("important_columns", []))
                        purpose = schema_obj.get("purpose", "")
                        
                        if tbl:
                            full_name = f"`{db_str}`.`{tbl}`" if db_str else f"`{tbl}`"
                            available_tables.append(full_name)
                            
                            # Rely on Qdrant's important_columns instead of querying real_schema again
                            rel_text = schema_obj.get("relationships", "")
                            summary = f"Table: {full_name}\nColumns: {cols}\nPurpose: {purpose}"
                            if rel_text:
                                summary += f"\nRelationships/Rules:\n{rel_text}"
                                
                            schema_summaries.append(summary)
                    except Exception:
                        pass
                        
            schema_text = "\n\n".join(schema_summaries)
            tables_list = ", ".join(available_tables)
            
        except Exception as e:
            logger.error(f"SQLAgent Qdrant fetch error: {e}")
            return "Error: Could not fetch schema."
        
        qdrant_elapsed = time.time() - qdrant_start
        logger.info(f"PERF | Qdrant search: {qdrant_elapsed:.3f}s | Found {len(results)} schemas")

        # 2. Ask LLM for raw SQL
        prompt = self.build_prompt(query, schema_text)
        llm_start = time.time()
        sql_query = await llm_service.generate(prompt=prompt, system="Output ONLY raw SQL.", temperature=0.0)
        llm_elapsed = time.time() - llm_start
        logger.info(f"PERF | SQL generation LLM: {llm_elapsed:.3f}s")
        import re
        sql_match = re.search(r'```(?:sql)?\s*(.*?)\s*```', sql_query, re.IGNORECASE | re.DOTALL)
        
        # Extract explanation text (everything before the SQL code block)
        explanation = sql_query.replace(sql_match.group(0) if sql_match else sql_query, "").strip()
        if not explanation:
            # Fallback if regex didn't split perfectly
            explanation_match = re.search(r'(.*?)(?:```sql|Generated SQL:)', sql_query, re.IGNORECASE | re.DOTALL)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
        
        if sql_match:
            sql_query = sql_match.group(1).strip()
        else:
            # Fallback extraction: Look for SELECT or WITH
            fallback_match = re.search(r'(SELECT|WITH)\s+.*', sql_query, re.IGNORECASE | re.DOTALL)
            if fallback_match:
                sql_query = fallback_match.group(0).strip()
            else:
                if "Generated SQL:" in sql_query:
                    sql_query = sql_query.split("Generated SQL:")[-1].strip()
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        logger.info(f"SQLAgent Generated Query:\n{sql_query}")
        
        if not sql_query:
            return "Could not generate SQL."
            
        if "I don't have enough schema information" in sql_query:
            return sql_query

        db_start = time.time()
        result_text = await self._execute_sql(
            connection_record.host, 
            connection_record.port, 
            connection_record.username, 
            decrypted_pw, 
            connection_record.database_name, 
            sql_query
        )
        
        # If the LLM generated an invalid query (e.g. hallucinated a column), retry SQL generation
        if result_text.startswith("Error:"):
            logger.warning(f"SQL failed: {result_text}")
            if "No database selected" in result_text or "doesn't exist" in result_text:
                logger.info("Skipping SQL retry because error is related to missing database or table.")
                return "Error: The required database or table does not exist. Please check your schema."
                
            logger.info(f"Retrying SQL generation with error feedback...")
            
            retry_prompt = f"""You previously generated this SQL:
```sql
{sql_query}
```
However, the database returned this exact error:
{result_text}

Using the schema context below, carefully analyze the error and fix the SQL query.
Pay special attention to column names and ensure you only use columns that exist in the schema.

[TABLE SCHEMA CONTEXT]
{schema_text}

Return ONLY your reasoning and the corrected SQL query in the exact same format as before.
"""
            retry_response = await llm_service.generate(prompt=retry_prompt, system="Output ONLY raw SQL.", temperature=0.0)
            
            # Extract explanation and retry SQL
            retry_sql_match = re.search(r'```(?:sql)?\s*(.*?)\s*```', retry_response, re.IGNORECASE | re.DOTALL)
            
            if retry_sql_match:
                retry_sql_query = retry_sql_match.group(1).strip()
            else:
                retry_sql_query = retry_response.replace("```sql", "").replace("```", "").strip()
                if "Generated SQL:" in retry_sql_query:
                    retry_sql_query = retry_sql_query.split("Generated SQL:")[-1].strip()
                    
            logger.info(f"Retried SQL Query:\n{retry_sql_query}")
            
            result_text = await self._execute_sql(
                connection_record.host, 
                connection_record.port, 
                connection_record.username, 
                decrypted_pw, 
                connection_record.database_name, 
                retry_sql_query
            )
            
            if result_text.startswith("Error:"):
                logger.error(f"Retry query also failed! Reason: {result_text}")
                return "Error: I couldn't retrieve the data because the database schema did not match the expected structure. Please verify the columns or refine your question."
        
        db_elapsed = time.time() - db_start
        
        total_elapsed = time.time() - total_start
        logger.info(
            f"PERF SUMMARY | "
            f"Qdrant: {qdrant_elapsed:.3f}s | "
            f"SQL Gen LLM: {llm_elapsed:.3f}s | "
            f"DB Exec: {db_elapsed:.3f}s | "
            f"TOTAL: {total_elapsed:.3f}s"
        )
        
        # Prepend the AI's explanation to the data table
        if explanation:
            return f"### Database Query Analysis:\n{explanation}\n\n{result_text}"
        return result_text

