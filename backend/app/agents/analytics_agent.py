import logging
from typing import Dict, Any
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

class AnalyticsAgent:
    """
    Analytics Agent
    Handles insights, bottlenecks, and root cause analysis.
    Executes a data query via SQL Agent and passes the result to the LLM for deep analysis.
    """
    
    async def generate_analytics(
        self, 
        query: str, 
        schema_context_str: str, 
        host: str, 
        port: int, 
        user: str, 
        encrypted_password: str, 
        db_name: str,
        mapping_hints: str = ""
    ) -> str:
        logger.info(f"AnalyticsAgent | Processing Query: '{query}'")

        from ..agents.sql_agent import sql_agent
        from cryptography.fernet import Fernet
        from ..core.config import settings
        
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(encrypted_password.encode()).decode()
        
        from ..agents.sql_validator_agent import sql_validator_agent
        
        max_retries = 3
        retry_count = 0
        error_feedback = ""
        raw_data = None
        sql = ""
        
        tables_in_context = sql_validator_agent.parse_schema_context(schema_context_str)

        # Use SQL Agent to get the raw data needed for analysis
        while retry_count <= max_retries:
            sql = await sql_agent.generate_sql(query, schema_context_str, mapping_hints, error_feedback)
            
            if sql.strip().upper() == "SCHEMA_ERROR":
                logger.warning("AnalyticsAgent | SQL Agent explicitly returned SCHEMA_ERROR. Aborting retries.")
                error_feedback = "SCHEMA_ERROR"
                break
                
            logger.info(f"AnalyticsAgent | Executing SQL (Attempt {retry_count + 1}): {sql}")
            
            val_result = sql_validator_agent.validate(sql, tables_in_context)
            if val_result != "Valid":
                error_feedback += f"\n- Failed Query: {sql}\n  Error: {val_result}\n"
                logger.warning(f"AnalyticsAgent | SQL Validation Failed: {val_result}")
                retry_count += 1
                continue
            
            try:
                raw_data = await sql_agent.execute_sql_raw(host, port, user, decrypted_pw, db_name, sql)
                break  # Success
            except Exception as e:
                error_feedback += f"\n- Failed Query: {sql}\n  Error: {str(e)}\n"
                logger.warning(f"AnalyticsAgent | Execution failed: {str(e)}")
                retry_count += 1
                
        if raw_data is None:
            return "I cannot fulfill this request because the necessary tables or columns (such as those related to your query) are missing from the database schema. Please ensure the correct tables exist and re-index the database."

        if not raw_data:
            return "No matching records were found for this analysis."

        # Pass raw data to LLM for insights
        return await self._generate_insights(query, raw_data)

    async def _generate_insights(self, query: str, raw_data: list) -> str:
        system_prompt = (
            "You are a Senior Data Analyst and Procurement Intelligence AI.\n"
            "Your task is to provide deep insights, explanations, and bottleneck analysis based on the provided data.\n"
            "RULES:\n"
            "1. Format your response with a Title, Key Insights (bullet points), and a brief Explanation.\n"
            "2. EXTREMELY STRICT RULE: Do NOT invent, guess, or suggest ANY external business reasons for the data trends. If a reason is not explicitly listed in the raw data, do not mention it. PERIOD.\n"
            "3. If the data only contains dates and numbers (e.g. Total Spend over time), your 'Explanation' section MUST be a maximum of 2 sentences long, simply describing the mathematical trend.\n"
            "4. If the user asks 'Why' something happened, and the data does not contain columns like 'SupplierName', 'Category', or 'Department' to answer it, you MUST replace the 'Explanation' section with the exact phrase: 'The retrieved data shows the numerical trend, but lacks the necessary dimensions to determine the root cause.'\n"
            "5. If the data DOES contain dimensional context (e.g. a specific supplier is failing), point it out directly using the data points.\n"
            "6. Be concise and professional. Do not expose SQL or raw technical structures.\n"
            "7. Format all currency and monetary values in Indian Rupees (₹ or INR), never in dollars.\n"
        )
        
        # Limit data to prevent token explosion
        data_preview = str(raw_data[:20]) if len(raw_data) > 20 else str(raw_data)
        
        final_prompt = (
            f"User Request: {query}\n\n"
            f"Data Result:\n{data_preview}\n\n"
            f"Please generate the insights and explanation."
        )
        
        return await llm_service.generate(prompt=final_prompt, system=system_prompt)

analytics_agent = AnalyticsAgent()
