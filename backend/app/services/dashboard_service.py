from .sql_service import sql_service

class DashboardService:
    async def generate_dashboard(self, query: str, schema_catalog: dict, db_conn_id: int, host: str, port: int, user: str, encrypted_password: str, db_name: str) -> dict:
        sql = await sql_service.generate_sql(query, schema_catalog)
        data = await sql_service.execute_query(sql, db_conn_id, host, port, user, encrypted_password, db_name)
        
        chart_type = "table"
        if data:
            keys = list(data[0].keys())
            if len(keys) >= 2:
                has_str = any(isinstance(data[0][k], str) for k in keys)
                has_num = any(isinstance(data[0][k], (int, float)) for k in keys)
                if has_str and has_num:
                    chart_type = "bar" if len(data) < 20 else "line"

        return {
            "title": f"Dashboard for: {query}",
            "chartType": chart_type,
            "data": {
                "labels": [str(row[keys[0]]) for row in data] if data else [],
                "datasets": [{
                    "label": keys[1] if len(keys) > 1 else "Value",
                    "data": [row[keys[1]] for row in data] if data and len(keys) > 1 else []
                }]
            },
            "summary": f"Generated {len(data)} records."
        }

dashboard_service = DashboardService()
