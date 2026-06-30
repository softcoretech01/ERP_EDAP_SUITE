from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.db_connection import DBConnection
from qdrant_client.models import Filter, FieldCondition, MatchValue

class TenantManager:
    @staticmethod
    def get_tenant_id_from_token(token_payload: dict) -> int:
        # Default to 1 if not present in payload (backward compatibility)
        return int(token_payload.get("tenant_id", 1))

    @staticmethod
    def get_tenant_filter(tenant_id: int, content_type: str = None) -> Filter:
        conditions = [
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value=tenant_id)
            )
        ]
        if content_type:
            conditions.append(
                FieldCondition(
                    key="type",
                    match=MatchValue(value=content_type)
                )
            )
        return Filter(must=conditions)

    @staticmethod
    async def get_tenant_connections(db: AsyncSession, tenant_id: int) -> List[DBConnection]:
        stmt = select(DBConnection).where(DBConnection.tenant_id == tenant_id, DBConnection.is_active == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_tenant_connection(db: AsyncSession, tenant_id: int, conn_id: int) -> DBConnection:
        stmt = select(DBConnection).where(
            DBConnection.id == conn_id, 
            DBConnection.tenant_id == tenant_id, 
            DBConnection.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalars().first()

tenant_manager = TenantManager()
