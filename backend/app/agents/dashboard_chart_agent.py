import logging
import re
from typing import Dict, Any
from ..services.sql_service import sql_service

logger = logging.getLogger(__name__)

class DashboardChartAgent:
    """
    Dashboard Chart Agent
    Detects user intent and generates dynamic dashboard chart data.
    """
    
    _TREND_PATTERNS = re.compile(r'\b(trend|monthly|yearly|compare|over time)\b', re.IGNORECASE)
    _PIE_PATTERNS = re.compile(r'\b(distribution|status|split|percentage)\b', re.IGNORECASE)
    _BAR_PATTERNS = re.compile(r'\b(top|highest|lowest|ranking|by|wise)\b', re.IGNORECASE)
    _KPI_PATTERNS = re.compile(r'\b(total|count|sum|value)\b', re.IGNORECASE)

    def _detect_chart_type(self, query: str) -> str:
        """Return one of: line, pie, bar, kpi"""
        if self._TREND_PATTERNS.search(query):
            return "line"
        if self._PIE_PATTERNS.search(query):
            return "pie"
        if self._BAR_PATTERNS.search(query):
            return "bar"
        if self._KPI_PATTERNS.search(query):
            return "kpi"
        return "table"  # Default fallback

    async def generate_dashboard_data(
        self, 
        query: str, 
        schema_context_str: str, 
        db_conn_id: int, 
        host: str, 
        port: int, 
        user: str, 
        encrypted_password: str, 
        db_name: str,
        mapping_hints: str = ""
    ) -> dict:
        # 1. Detect Chart Type
        chart_type = self._detect_chart_type(query)
        logger.info(f"DashboardChartAgent | Query: '{query}' | Detected Chart Type: {chart_type}")

        # 2. Generate SQL using sql_agent and execute using sql_agent.execute_sql_raw
        from ..agents.sql_agent import sql_agent
        from cryptography.fernet import Fernet
        from ..core.config import settings
        
        from ..agents.sql_validator_agent import sql_validator_agent
        
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(encrypted_password.encode()).decode()
        
        max_retries = 3
        retry_count = 0
        error_feedback = ""
        raw_data = None
        sql = ""
        
        tables_in_context = sql_validator_agent.parse_schema_context(schema_context_str)
        
        # 3. Resolve Columns (Intent Parsing)
        from ..services.dashboard_column_resolver import dashboard_column_resolver
        resolved_columns = await dashboard_column_resolver.resolve_columns(query, schema_context_str)
        
        if resolved_columns.get("status") == "SCHEMA_ERROR":
            logger.warning(f"DashboardChartAgent | Column Resolver failed: {resolved_columns.get('error')}")
            return {
                "chartType": "table",
                "title": "Data Unavailable",
                "summary": f"Missing required data: {resolved_columns.get('error')}",
                "data": {"labels": [], "datasets": []}
            }
            
        # Inject the resolved columns directly into the mapping hints
        resolved_hints = f"\nCRITICAL MAPPING FROM INTENT PARSER:\n- Primary Table: {resolved_columns.get('primary_table')}\n"
        if resolved_columns.get("date_column"):
            resolved_hints += f"- EXACT Date Column to use: {resolved_columns.get('date_column')}\n"
        if resolved_columns.get("metric_column"):
            resolved_hints += f"- EXACT Metric/Amount Column to use: {resolved_columns.get('metric_column')}\n"
            
        # Add output shape constraints based on Chart Planner
        shape_hints = "\nCRITICAL OUTPUT CONSTRAINTS (CHART PLANNER):\n"
        if chart_type in ["line", "bar", "pie"]:
            shape_hints += "- You MUST return EXACTLY 2 columns.\n"
            shape_hints += "- Column 1: The label or date (e.g., date, category). If grouping by a date column, ALWAYS format it as Year-Month (e.g., DATE_FORMAT(col, '%Y-%m')) and GROUP BY it, unless a specific format like daily/yearly is requested.\n"
            shape_hints += "- Column 2: The aggregated metric (e.g., COUNT(*), SUM(amount)).\n"
            shape_hints += "- DO NOT return 3 or more columns! Group appropriately.\n"
        elif chart_type == "kpi":
            shape_hints += "- You MUST return EXACTLY 1 column containing the aggregated value.\n"
            shape_hints += "- DO NOT group by date or ID unless computing an average.\n"
            
        mapping_hints = (mapping_hints or "") + resolved_hints + shape_hints

        # REDUCED RETRIES: For dashboard speed, if we can't get it in 1 retry, fail fast.
        max_retries = 1

        while retry_count <= max_retries:
            sql = await sql_agent.generate_sql(query, schema_context_str, mapping_hints, error_feedback)
            
            if sql.strip().upper() == "SCHEMA_ERROR":
                logger.warning("DashboardChartAgent | SQL Agent explicitly returned SCHEMA_ERROR. Aborting retries.")
                error_feedback = "SCHEMA_ERROR"
                break
                
            # FAST AUTO-CORRECTION: Small local LLMs often ignore negative constraints and hallucinate 'CreatedDate' or 'Amount'.
            # We auto-replace them with our heuristically resolved columns to prevent a slow retry loop.
            import re
            if resolved_columns.get("date_column"):
                sql = re.sub(r'(?i)\bCreatedDate\b', resolved_columns["date_column"], sql)
                sql = re.sub(r'(?i)\bDate\b', resolved_columns["date_column"], sql)
            if resolved_columns.get("metric_column"):
                sql = re.sub(r'(?i)\bAmount\b', resolved_columns["metric_column"], sql)
                sql = re.sub(r'(?i)\bTotalAmount\b', resolved_columns["metric_column"], sql)
                
            # Common typo auto-corrections for master columns
            sql = re.sub(r'(?i)\bprno\b', 'PR_Number', sql)
            sql = re.sub(r'(?i)\bponumber\b', 'pono', sql)
            
            logger.info(f"DashboardChartAgent | Executing SQL (Attempt {retry_count + 1}): {sql}")
            
            val_result = await sql_validator_agent.validate(sql, tables_in_context)
            if val_result.startswith("Error:"):
                error_feedback += f"\n- Failed Query: {sql}\n  {val_result}\n"
                logger.warning(f"DashboardChartAgent | SQL Validation Failed: {val_result}")
                retry_count += 1
                continue
                
            # Use the AST-auto-corrected SQL
            sql = val_result
            
            try:
                raw_data = await sql_agent.execute_sql_raw(host, port, user, decrypted_pw, db_name, sql)
                break  # Success
            except Exception as e:
                error_feedback += f"\n- Failed Query: {sql}\n  Error: {str(e)}\n"
                logger.warning(f"DashboardChartAgent | Execution failed: {str(e)}")
                retry_count += 1
                
        if raw_data is None:
            # All retries failed
            return {
                "chartType": "table",
                "title": "Data Unavailable",
                "summary": "I cannot fulfill this request because the necessary tables or columns (such as those related to your query) are missing from the database schema. Please ensure the correct tables exist and re-index the database.",
                "data": {"labels": [], "datasets": []}
            }
        # 3. Format into Chart JSON
        if not raw_data:
            return {
                "chartType": "table",
                "title": "No Data Found",
                "summary": "No matching records were found for this query.",
                "data": {"labels": [], "datasets": []}
            }

        keys = list(raw_data[0].keys())
        
        # Format based on Chart Type
        if chart_type == "kpi":
            # Just take the very first value of the first row
            kpi_value = raw_data[0][keys[0]] if keys else 0
            
            # Format numbers properly for KPI
            formatted_val = self._format_kpi_value(kpi_value)
            
            return {
                "chartType": "kpi",
                "title": query.title(),
                "summary": "Key Performance Indicator",
                "data": {
                    "labels": [keys[0] if keys else "Value"],
                    "datasets": [{"label": keys[0] if keys else "Value", "data": [kpi_value], "formattedValue": formatted_val}]
                }
            }
            
        else:
            # Handle line, bar, pie, table
            labels = []
            dataset_data = []
            
            # Determine which column is label and which is value
            label_key = keys[0]
            val_key = keys[1] if len(keys) > 1 else keys[0]
            
            # Smart detection: If the first column is a number and second is a string, swap them
            if len(keys) > 1:
                if isinstance(raw_data[0][keys[0]], (int, float)) and isinstance(raw_data[0][keys[1]], str):
                    label_key = keys[1]
                    val_key = keys[0]
                    
            for row in raw_data:
                labels.append(str(row[label_key]))
                # Ensure data is a number
                val = row[val_key]
                dataset_data.append(float(val) if val is not None else 0)

            # Cap pie charts to top 10 to avoid clutter
            if chart_type == "pie" and len(labels) > 10:
                labels = labels[:10]
                dataset_data = dataset_data[:10]
                
            # If line/bar but only 1 row returned, might be better as a KPI
            if len(raw_data) == 1 and chart_type in ["line", "bar"]:
                chart_type = "kpi"
                formatted_val = self._format_kpi_value(dataset_data[0])
                return {
                    "chartType": "kpi",
                    "title": query.title(),
                    "summary": "Single Metric Detected",
                    "data": {
                        "labels": [val_key],
                        "datasets": [{"label": val_key, "data": [dataset_data[0]], "formattedValue": formatted_val}]
                    }
                }

            return {
                "chartType": chart_type,
                "title": query.title(),
                "summary": f"Data retrieved based on {len(raw_data)} records.",
                "data": {
                    "labels": labels,
                    "datasets": [{
                        "label": val_key,
                        "data": dataset_data
                    }]
                }
            }

    def _format_kpi_value(self, value: Any) -> str:
        """Formats KPI numbers to INR Indian system."""
        try:
            num = float(value)
            if num >= 10000000:
                return f"INR {num / 10000000:,.2f} Crores"
            elif num >= 100000:
                return f"INR {num / 100000:,.2f} Lakhs"
            else:
                return f"{num:,.2f}".rstrip('0').rstrip('.')
        except (ValueError, TypeError):
            return str(value)

dashboard_chart_agent = DashboardChartAgent()
