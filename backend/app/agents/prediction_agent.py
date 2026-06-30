import logging
import math
from typing import Dict, Any, List
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

class PredictionAgent:
    """
    Prediction Agent
    Provides forecasting and risk prediction based on historical data.
    """
    
    async def generate_prediction(
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
        logger.info(f"PredictionAgent | Processing Query: '{query}'")

        from ..agents.sql_agent import sql_agent
        from cryptography.fernet import Fernet
        from ..core.config import settings
        
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(encrypted_password.encode()).decode()
        
        from ..agents.sql_validator_agent import sql_validator_agent
        
        # We need historical data for prediction, so we instruct the SQL agent 
        # to generate a time-series or historical trend query.
        prediction_instruction = "IMPORTANT: For prediction/forecast queries, generate SQL that returns historical time-series data (e.g. grouped by month or week) so we can forecast the next period."
        
        max_retries = 3
        retry_count = 0
        error_feedback = ""
        raw_data = None
        sql = ""
        
        tables_in_context = sql_validator_agent.parse_schema_context(schema_context_str)

        while retry_count <= max_retries:
            sql = await sql_agent.generate_sql(query, schema_context_str, f"{prediction_instruction}\nMapping Hints: {mapping_hints}", error_feedback)
            
            if sql.strip().upper() == "SCHEMA_ERROR":
                logger.warning("PredictionAgent | SQL Agent explicitly returned SCHEMA_ERROR. Aborting retries.")
                error_feedback = "SCHEMA_ERROR"
                break
                
            logger.info(f"PredictionAgent | Executing SQL (Attempt {retry_count + 1}): {sql}")
            
            val_result = sql_validator_agent.validate(sql, tables_in_context)
            if val_result != "Valid":
                error_feedback += f"\n- Failed Query: {sql}\n  Error: {val_result}\n"
                logger.warning(f"PredictionAgent | SQL Validation Failed: {val_result}")
                retry_count += 1
                continue
            
            try:
                raw_data = await sql_agent.execute_sql_raw(host, port, user, decrypted_pw, db_name, sql)
                break
            except Exception as e:
                error_feedback += f"\n- Failed Query: {sql}\n  Error: {str(e)}\n"
                logger.warning(f"PredictionAgent | Execution failed: {str(e)}")
                retry_count += 1
                
        if raw_data is None:
            return "I cannot fulfill this request because the necessary tables or columns (such as those related to your query) are missing from the database schema. Please ensure the correct tables exist and re-index the database."

        if not raw_data:
            return "No historical records found to generate a prediction."

        # Attempt to calculate a simple statistical forecast
        forecast_data = self._calculate_basic_forecast(raw_data)
        
        # Pass to LLM to generate the final formatted response
        return await self._generate_forecast_response(query, raw_data, forecast_data)

    def _calculate_basic_forecast(self, data: List[Dict[str, Any]]) -> dict:
        """
        Attempts to extract numerical values from the time series and calculate 
        a simple moving average / linear regression for the next period.
        """
        if len(data) < 2:
            return {"status": "insufficient_data", "message": "Not enough historical data points to calculate a reliable statistical forecast."}
            
        try:
            # Try to find a numeric column that represents the metric
            # We assume the first non-string/non-date column is the target metric
            target_col = None
            for key, val in data[0].items():
                if isinstance(val, (int, float)):
                    target_col = key
                    break
                    
            if not target_col:
                # If no direct numeric type, try to cast
                for key, val in data[0].items():
                    try:
                        float(val)
                        target_col = key
                        break
                    except (ValueError, TypeError):
                        pass
                        
            if not target_col:
                return {"status": "error", "message": "Could not identify a numerical metric for forecasting."}
                
            values = [float(row[target_col]) for row in data if row[target_col] is not None]
            
            if len(values) < 2:
                return {"status": "insufficient_data", "message": "Not enough numerical data points."}
                
            # Simple Linear Regression (y = mx + c)
            n = len(values)
            x_sum = sum(range(n))
            y_sum = sum(values)
            xy_sum = sum(i * values[i] for i in range(n))
            x_sq_sum = sum(i ** 2 for i in range(n))
            
            denominator = (n * x_sq_sum - x_sum ** 2)
            if denominator == 0:
                slope = 0
            else:
                slope = (n * xy_sum - x_sum * y_sum) / denominator
                
            intercept = (y_sum - slope * x_sum) / n
            
            # Predict next period (x = n)
            next_val = slope * n + intercept
            
            # Calculate simple confidence score based on R-squared approximation or variance
            # For simplicity, we assign a rough confidence based on the number of data points and trend consistency
            variance = sum((y - (slope * i + intercept)) ** 2 for i, y in enumerate(values))
            mean_y = y_sum / n if n > 0 else 1
            if mean_y == 0:
                mean_y = 1
            
            error_margin = math.sqrt(variance / n) / mean_y
            confidence = max(0, min(100, int(100 - (error_margin * 100))))
            
            # Boost confidence slightly if we have more data points
            if n > 12: confidence = min(100, confidence + 10)
            if n < 5: confidence = max(0, confidence - 20)
            
            return {
                "status": "success",
                "metric": target_col,
                "forecast_value": next_val,
                "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
                "confidence_score": f"{confidence}%",
                "data_points_used": n
            }
        except Exception as e:
            logger.error(f"Statistical forecast failed: {e}")
            return {"status": "error", "message": str(e)}


    async def _generate_forecast_response(self, query: str, raw_data: list, forecast_data: dict) -> str:
        system_prompt = (
            "You are a Senior Data Scientist and Procurement Intelligence AI.\n"
            "Your task is to provide a predictive forecast or risk assessment based on historical data and the provided statistical calculations.\n"
            "RULES:\n"
            "1. Format your response with a Title, Forecast Prediction (highlight the calculated next value), Confidence Score, and a brief Risk/Trend Explanation.\n"
            "2. EXTREMELY STRICT RULE: Do NOT invent, guess, or suggest ANY external business reasons for the forecast. If a reason is not explicitly listed in the raw data, do not mention it. PERIOD.\n"
            "3. If the statistical forecast says 'insufficient_data' or 'error', state that clearly and provide a qualitative assessment based ONLY on the mathematical properties of the raw data instead.\n"
            "4. Format currency values in Indian Rupees (₹ or INR).\n"
        )
        
        data_preview = str(raw_data[:20]) if len(raw_data) > 20 else str(raw_data)
        
        final_prompt = (
            f"User Request: {query}\n\n"
            f"Statistical Forecast Calculation:\n{forecast_data}\n\n"
            f"Historical Raw Data:\n{data_preview}\n\n"
            f"Please generate the formatted prediction response."
        )
        
        return await llm_service.generate(prompt=final_prompt, system=system_prompt)

prediction_agent = PredictionAgent()
