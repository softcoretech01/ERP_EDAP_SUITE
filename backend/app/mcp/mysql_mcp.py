import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.connection_manager import connection_manager
from ..services.sql_validator import sql_validator

logger = logging.getLogger(__name__)

class MySQLMCP:
    """
    Model Context Protocol (MCP) layer for MySQL/MariaDB/PostgreSQL databases.
    Provides tools for the AI agents to interact with customer databases safely.
    """
    def __init__(self):
        pass

    async def execute_read_query(self, connection_id: int, tenant_id: int, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Executes a SELECT query on the specified database connection.
        Ensures safety by using the sql_validator before execution.
        """
        # 1. Validate the query (ensure it's a SELECT, enforce LIMIT, etc.)
        is_valid, error_msg = sql_validator.validate_read_only(query)
        if not is_valid:
            raise ValueError(f"Invalid query: {error_msg}")
            
        safe_query = sql_validator.enforce_limit(query, limit)
        
        # 2. Get connection and execute
        async with connection_manager.get_tenant_session(tenant_id, connection_id) as session:
            result = await session.execute(text(safe_query))
            keys = result.keys()
            rows = result.fetchall()
            
            return [dict(zip(keys, row)) for row in rows]

mysql_mcp = MySQLMCP()
