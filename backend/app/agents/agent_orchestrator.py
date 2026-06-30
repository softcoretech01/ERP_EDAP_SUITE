import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import time

from .router_agent import router_agent
from .schema_retrieval_agent import schema_retrieval_agent
from .sql_agent import sql_agent
from .sql_validator_agent import sql_validator_agent
from .memory_agent import memory_agent
from .response_formatter_agent import response_formatter_agent
from .query_classifier_agent import query_classifier_agent
from .analytics_agent import analytics_agent
from .prediction_agent import prediction_agent
from .dashboard_chart_agent import DashboardChartAgent
from ..services.llm_service import llm_service
from ..core.tenant_manager import tenant_manager

dashboard_chart_agent = DashboardChartAgent()

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Central orchestrator implementing the 4-Agent Architecture.
    """
    def __init__(self):
        pass

    async def process_request(self, db: AsyncSession, user_id: int, tenant_id: int, session_id: str, query: str, mode: str = "db") -> str:
        total_start = time.time()
        
        # 1. Fetch conversational context
        context = await memory_agent.get_context(db, session_id, limit=3)
        
        # Handle document mode quickly
        if mode == "document":
            from ..services.rag_service import rag_service
            rag_context = await rag_service.get_raw_context(tenant_id, query, top_k=15)
            context += f"\n\n[Documentation Data]:\n{rag_context}"
            return await self._generate_final_response(context, query)
            
        # --- 4-Agent Pipeline ---
        
        # Agent 0: Query Classifier
        query_category = query_classifier_agent.classify_query(query)
        logger.info(f"Query classified as: {query_category}")
        
        # Agent 1: Router + Intent
        router_start = time.time()
        module, intent_keywords = await router_agent.route_intent(query)
        logger.info(f"Agent 1 (Router) took {time.time() - router_start:.3f}s")
        
        if module == "general" or intent_keywords.lower() == "general":
            return await self._generate_general_response(context, query)

        if module == "document" or "document" in intent_keywords.lower():
            # Fallback to document agent
            return await self.process_request(db, user_id, tenant_id, session_id, query, mode="document")

        # Get DB Credentials once
        connections = await tenant_manager.get_tenant_connections(db, tenant_id)
        if not connections:
            return "Error: No active database connection found for this workspace."
            
        conn_record = connections[0]
        from cryptography.fernet import Fernet
        from ..core.config import settings
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(conn_record.encrypted_password.encode()).decode()

        # Agent 2: Schema Retrieval
        schema_start = time.time()
        from ..services.relationship_graph import relationship_graph
        if not relationship_graph._is_loaded:
            await relationship_graph.build_graph(db, conn_record.database_name)
        schema_context_str = await schema_retrieval_agent.retrieve_schema_context(tenant_id, module, intent_keywords)
        logger.info(f"Agent 2 (Retrieval) took {time.time() - schema_start:.3f}s")
        
        if "No relevant schema found" in schema_context_str:
            return "Error: Could not retrieve relevant schema. Please clarify your query."

        # Schema-Aware Synonym Engine
        from ..services.synonym_service import synonym_service
        mapping_hints = await synonym_service.augment_query(query, module, schema_context_str)
        if mapping_hints:
            logger.info(f"Injected mapping hints: {mapping_hints}")

        # Route to Specialized Agents (Analytics, Trend, Prediction)
        if query_category == "analytics":
            return await analytics_agent.generate_analytics(query, schema_context_str, conn_record.host, conn_record.port, conn_record.username, conn_record.encrypted_password, conn_record.database_name, mapping_hints)
        elif query_category == "prediction":
            return await prediction_agent.generate_prediction(query, schema_context_str, conn_record.host, conn_record.port, conn_record.username, conn_record.encrypted_password, conn_record.database_name, mapping_hints)
        elif query_category == "trend":
            import json
            chart_data = await dashboard_chart_agent.generate_dashboard_data(query, schema_context_str, conn_record.id, conn_record.host, conn_record.port, conn_record.username, conn_record.encrypted_password, conn_record.database_name, mapping_hints)
            return json.dumps(chart_data)

        # Parse context_str back into table/column dicts for AST validation
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

        max_retries = 3
        retry_count = 0
        sql_result = ""
        error_feedback = ""

        while retry_count <= max_retries:
            # Agent 3: SQL Generation
            sql_start = time.time()
            generated_sql = await sql_agent.generate_sql(query, schema_context_str, mapping_hints, error_feedback)
            logger.info(f"Agent 3 (SQL Gen) took {time.time() - sql_start:.3f}s (Attempt {retry_count + 1})")
            
            # Agent 4: SQL Validation
            if generated_sql.strip().upper() == "SCHEMA_ERROR":
                logger.warning("SQL Agent explicitly returned SCHEMA_ERROR. Aborting retries.")
                error_feedback = "SCHEMA_ERROR"
                return "I cannot fulfill this request because the necessary tables or columns (such as those related to invoices) are missing from the database schema. Please ensure the correct tables exist and re-index the database."
                
            val_start = time.time()
            val_result = sql_validator_agent.validate(generated_sql, tables_in_context)
            logger.info(f"Agent 4 (SQL Val) took {time.time() - val_start:.3f}s")
            
            if val_result != "Valid":
                error_feedback += f"\n- Failed Query: {generated_sql}\n  Error: {val_result}\n"
                retry_count += 1
                logger.warning(f"SQL Validation Failed. Retrying ({retry_count}/{max_retries})")
                continue
                
            # Execute SQL
            exec_start = time.time()
            sql_result = await sql_agent.execute_sql(
                conn_record.host, 
                conn_record.port, 
                conn_record.username, 
                decrypted_pw, 
                conn_record.database_name, 
                generated_sql
            )
            logger.info(f"SQL Execution took {time.time() - exec_start:.3f}s")
            
            if sql_result.startswith("Error:"):
                error_feedback += f"\n- Failed Query: {generated_sql}\n  Error: {sql_result}\n"
                retry_count += 1
                logger.warning(f"SQL Execution Failed. Retrying ({retry_count}/{max_retries})")
                continue
                
            break
            
        if retry_count > max_retries:
            # Route failure through formatter — never expose raw error to user
            logger.error(f"All retries exhausted. Last error: {error_feedback}")
            return "I couldn't retrieve the information you requested. Please try rephrasing your question or check that the relevant data exists."

        # Agent 5: Response Formatter — converts raw SQL result into business response
        # IMPORTANT: Do NOT inject sql_result into the context with the '[Raw Database Data]' label.
        # That label causes the LLM to echo it verbatim in its output.
        # Instead, pass sql_result directly to the formatter which handles it safely.
        fmt_start = time.time()
        final_resp = await response_formatter_agent.format(
            user_query=query,
            sql_result=sql_result,
            conversation_context=context  # prior conversation turns only
        )
        logger.info(f"Agent 5 (Formatter) took {time.time() - fmt_start:.3f}s")
        logger.info(f"TOTAL PIPELINE TIME: {time.time() - total_start:.3f}s")

        # 5. Save to memory
        from ..services.memory_service import memory_service
        await memory_service.save_interaction(db, session_id, user_id, query, final_resp)

        return final_resp

    async def _generate_general_response(self, context: str, query: str) -> str:
        system_prompt = (
            "You are a highly capable and helpful ERP AI Business Assistant.\n"
            "The user is asking a general knowledge question, asking for a definition, or making a conversational greeting.\n"
            "Use your vast built-in knowledge to answer the question thoroughly and accurately.\n"
            "If they ask for definitions or explanations (like 'Define PR' or 'What is an invoice'), provide a clear, business-focused definition and explanation.\n"
            "If they just say 'hi', respond in a friendly, professional manner and explain that you can help them analyze ERP data, search documents, or answer business questions.\n"
            "Keep your answer helpful, professional, and well-structured."
        )
        final_prompt = f"Conversation Context:\n{context}\n\nUser Query:\n{query}"
        return await llm_service.generate(prompt=final_prompt, system=system_prompt)

    async def _generate_final_response(self, context: str, query: str) -> str:
        system_prompt = (
            "You are an ERP AI Business Assistant. Your job is to convert data results into clean, professional, business-friendly responses.\n\n"

            "====================================================\n"
            "CORE RULES\n"
            "==========\n\n"

            "RULE 1 — NEVER expose technical/backend terms to users.\n"
            "Never mention: Raw Database Data, SQL Query, Executed SQL, Database Result, Schema, Table Name, Column Name, Module Detection, Query Classification.\n"
            "BAD: 'Based on the provided Raw Database Data...'\n"
            "GOOD: 'Purchase Order Summary'\n\n"

            "RULE 2 — NEVER hallucinate.\n"
            "Only answer using actual retrieved data.\n"
            "If comparison data (last month / last year) is NOT available, DO NOT mention trends.\n"
            "BAD: 'Purchase orders increased compared to last month' (only valid if comparison data exists)\n"
            "GOOD: 'Trend data is unavailable for comparison.'\n\n"

            "RULE 3 — Format numbers professionally.\n"
            "Examples:\n"
            "  2959            → 2,959\n"
            "  8532910195.5450 → 8,532,910,195.55\n"
            "  8532910195.5450 INR → ₹ 8,532.9 Crores\n"
            "  1250000         → 1.25M\n"
            "  2500000000      → 2.5B\n\n"
            "Indian number system rules:\n"
            "  1 Lakh  = 100,000 | 1 Crore = 10,000,000\n"
            "  value >= 10,000,000 → '₹ X Crores' (divide by 10,000,000)\n"
            "  value >= 100,000    → '₹ X Lakhs'  (divide by 100,000)\n"
            "  value <  100,000    → '₹ X,XXX' (comma formatted)\n"
            "  CRITICAL: NEVER use Dollars ($). ALWAYS use Indian Rupees (₹ or INR) for monetary values.\n"
            "  Always prefix monetary values with ₹ or INR. Round to 2 decimal places max.\n"
            "  NEVER lose accuracy: ₹ 8,532.9 Crores is NOT ₹ 853.3 Crores.\n"
            "Always format: counts, currency, percentages, quantities.\n\n"

            "RULE 4 — Keep response concise and professional.\n"
            "Responses should feel like an ERP dashboard, business copilot, or executive summary. Avoid robotic wording.\n\n"

            "====================================================\n"
            "RESPONSE FORMAT RULES\n"
            "=====================\n\n"

            "A) SIMPLE KPI QUERY (how many, total count, number of)\n"
            "Format:\n"
            "  [Title]\n"
            "  • Main Metric\n"
            "Example:\n"
            "  Purchase Request Summary\n"
            "  • Total Purchase Requests: 2,959\n\n"

            "B) AGGREGATION QUERY (total value, total amount, total sales)\n"
            "Format:\n"
            "  [Title]\n"
            "  • Main Metric\n"
            "  • Optional short explanation\n"
            "Example:\n"
            "  Purchase Order Summary\n"
            "  • Total Active PO Value: INR 8,532.9 Crores\n"
            "  This represents the total value of all active purchase orders.\n\n"

            "C) LIST QUERY (show, list, find, pending, overdue)\n"
            "Format:\n"
            "  [Title]\n"
            "  Found X records.\n"
            "  [Record list in readable format]\n"
            "Example:\n"
            "  Pending Purchase Orders\n"
            "  Found 24 orders.\n"
            "  PO-1001 | ABC Supplier | Pending\n"
            "  PO-1002 | XYZ Supplier | Pending\n\n"

            "D) TREND QUERY (compare with last month, yearly, trend) — ONLY use if comparison data EXISTS.\n"
            "Format:\n"
            "  [Title]\n"
            "  • Current Value\n"
            "  • Previous Value\n"
            "  • Change %\n"
            "  Insight: Short factual insight.\n"
            "Example:\n"
            "  Purchase Order Trend Analysis\n"
            "  • Current Month: INR 8,532.9 Crores\n"
            "  • Last Month: INR 7,980.4 Crores\n"
            "  • Change: +6.9%\n"
            "  Insight: Purchase order value increased by 6.9% compared to last month.\n\n"

            "E) ANALYTICS QUERY (why, insights, suggest improvements) — only provide insights supported by data.\n"
            "Format:\n"
            "  [Title]\n"
            "  Metrics\n"
            "  Insight\n"
            "  Recommendation\n\n"

            "====================================================\n"
            "STRICT RESTRICTIONS\n"
            "===================\n\n"

            "1. NEVER show internal labels: SIMPLE KPI QUERY, TREND QUERY, AGGREGATION QUERY\n"
            "2. NEVER invent: trends, comparisons, causes, business reasons\n"
            "3. NEVER over-explain simple questions.\n"
            "   If user asks 'What is total PO value?' — answer ONLY that. No trend, no suggestions.\n\n"

            "====================================================\n"
            "ERROR HANDLING\n"
            "==============\n\n"

            "If data unavailable: 'I couldn't find sufficient data to answer this question.'\n"
            "If query result empty: 'No matching records were found.'\n\n"

            "====================================================\n"
            "DATA SOURCE RULES\n"
            "=================\n\n"

            "1. Use ONLY numbers from the data block at the END of the context.\n"
            "2. Old conversation history is background context ONLY — never reuse old numbers for the current answer.\n"
            "3. If data retrieval failed or is empty, say: 'The requested information could not be retrieved. Please try rephrasing your question.'\n"
        )
        final_prompt = f"Context & Data:\n{context}\n\nUser Query:\n{query}"
        print("--- FINAL PROMPT ---")
        print(final_prompt.encode("ascii", errors="replace").decode("ascii"))
        print("--------------------")
        return await llm_service.generate(prompt=final_prompt, system=system_prompt)

agent_orchestrator = AgentOrchestrator()

