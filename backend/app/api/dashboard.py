import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db.database import get_db, test_db_connection
from ..db.connection_manager import connection_manager
from ..auth.permissions import RequiresPermission
from ..services.dashboard_service import dashboard_service
from ..services.schema_service import schema_service
from ..models.db_connection import DBConnection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("")
async def get_dashboard(query: str, db_conn_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch connection record
    stmt = select(DBConnection).where(DBConnection.id == db_conn_id, DBConnection.is_active == True)
    result = await db.execute(stmt)
    connection_record = result.scalars().first()
    
    if not connection_record:
        return {
            "success": False,
            "type": "error",
            "message": "Database connection not found or inactive"
        }

    # Connection manager validation
    is_connected = await connection_manager.validate_connection(
        db_conn_id=db_conn_id,
        host=connection_record.host,
        port=connection_record.port,
        user=connection_record.username,
        encrypted_password=connection_record.encrypted_password,
        db_name=connection_record.database_name
    )
    if not is_connected:
        return {
            "success": False,
            "type": "error",
            "message": "Database connection unavailable"
        }
        
    try:
        from ..agents.router_agent import router_agent
        from ..agents.schema_retrieval_agent import schema_retrieval_agent
        from ..agents.dashboard_chart_agent import dashboard_chart_agent
        
        module, intent_keywords = await router_agent.route_intent(query)
        schema_context_str = await schema_retrieval_agent.retrieve_schema_context(connection_record.tenant_id, module, intent_keywords)
        
        if "No relevant schema found" in schema_context_str:
            return {
                "success": False,
                "type": "error",
                "message": "Could not find relevant tables for this query. Please clarify your query."
            }

        data = await dashboard_chart_agent.generate_dashboard_data(
            query, schema_context_str, db_conn_id, connection_record.host, connection_record.port, connection_record.username, connection_record.encrypted_password, connection_record.database_name
        )
        return {
            "success": True,
            "type": "dashboard",
            "result": data
        }
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        return {
            "success": False,
            "type": "error",
            "message": str(e) or "Failed to generate dashboard data"
        }
