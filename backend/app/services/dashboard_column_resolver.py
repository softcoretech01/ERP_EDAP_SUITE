import logging
import json
from typing import Dict, Any
from .llm_service import llm_service
from ..agents.sql_validator_agent import sql_validator_agent

logger = logging.getLogger(__name__)

class DashboardColumnResolver:
    """
    Parses user intent and maps it directly to explicitly validated schema columns.
    Prevents the LLM from hallucinating generic columns.
    """
    
    async def resolve_columns(self, query: str, schema_context_str: str) -> Dict[str, Any]:
        """
        Parses intent and resolves exact column names from the provided schema context.
        Returns a JSON object like:
        {
            "primary_table": "tbl_purchaseorder_header",
            "date_column": "podate",
            "metric_column": "nettotal",
            "status": "success",
            "error": ""
        }
        """
        
        system_prompt = """
        You are a strict Schema Column Resolver for an ERP system.
        Your job is to analyze the user's dashboard query and the provided database schema, and extract the EXACT physical column names needed to answer the query.
        
        RULES:
        1. NEVER invent or hallucinate column names. (e.g., do NOT use `CreatedDate` if it is not in the schema context).
        2. You MUST pick columns strictly from the provided SCHEMA CONTEXT.
        3. If you cannot find a required column in the schema, return status "SCHEMA_ERROR".
        4. Date Column Priority: Prefer business dates (like `podate`, `prdate`) over audit dates (like `createddt`) if both exist, unless the user specifically asks for creation trends.
        5. Respond ONLY with valid JSON.
        
        JSON SCHEMA:
        {
            "primary_table": "<exact_table_name_from_schema>",
            "date_column": "<exact_date_column_name_or_null>",
            "metric_column": "<exact_metric_column_name_or_null>",
            "status": "success" | "SCHEMA_ERROR",
            "error": "<description of missing data if SCHEMA_ERROR, else empty string>"
        }
        """
        
        user_prompt = f"""
        USER QUERY: {query}
        
        SCHEMA CONTEXT:
        {schema_context_str}
        
        Resolve the columns and return JSON:
        """
        
        try:
            import re
            
            tables = sql_validator_agent.parse_schema_context(schema_context_str)
            allowed_tables = {t["table_name"].lower().split('.')[-1].strip('`'): [c.lower() for c in t["columns"]] for t in tables}
            
            if not allowed_tables:
                return {"status": "SCHEMA_ERROR", "error": "No schema available in context."}
                
            query_lower = query.lower()
            
            # 1. Primary Table (Most relevant from vector DB is always first)
            primary_table = list(allowed_tables.keys())[0]
            primary_cols = allowed_tables[primary_table]
            
            # 2. Resolve Date Column Heuristically
            date_col = None
            date_keywords = ['date', 'day', 'month', 'year', 'daily', 'monthly', 'yearly', 'trend', 'time', 'when', 'today', 'this month']
            if any(kw in query_lower for kw in date_keywords):
                # Priority 1: Business dates
                for candidate in ['podate', 'prdate', 'invoicedate', 'grndate']:
                    if candidate in primary_cols:
                        date_col = candidate
                        break
                # Priority 2: Audit dates (only if business date not found)
                if not date_col:
                    for candidate in ['createddt', 'createddate', 'entrydate']:
                        if candidate in primary_cols:
                            date_col = candidate
                            break
                            
            # 3. Resolve Metric/Amount Column Heuristically
            metric_col = None
            metric_keywords = ['spend', 'value', 'amount', 'total', 'cost', 'sum']
            if any(kw in query_lower for kw in metric_keywords):
                for candidate in ['nettotal', 'amount', 'totalamount', 'grandtotal', 'subtotal', 'balance']:
                    if candidate in primary_cols:
                        metric_col = candidate
                        break
                        
            resolved_data = {
                "primary_table": primary_table,
                "date_column": date_col,
                "metric_column": metric_col,
                "status": "success"
            }
            return resolved_data
            
        except Exception as e:
            logger.error(f"Failed to resolve columns: {e}")
            return {"status": "SCHEMA_ERROR", "error": "Failed to parse resolver heuristics."}

dashboard_column_resolver = DashboardColumnResolver()
