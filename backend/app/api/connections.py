import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..db.database import get_db
from ..auth.permissions import get_current_user_token
from ..core.tenant_manager import tenant_manager
from ..models.db_connection import DBConnection

from cryptography.fernet import Fernet
from ..core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

class ConnectionCreate(BaseModel):
    name: str
    host: str
    port: int
    user: str
    password: str
    db_name: str = ""
    db_type: str = "mysql"

class ConnectionResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    user: str
    db_name: str
    db_type: str
    is_active: bool
    connection_status: str
    last_indexed_at: str | None = None
    error_message: str | None = None

@router.get("", response_model=List[ConnectionResponse])
async def list_connections(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    connections = await tenant_manager.get_tenant_connections(db, tenant_id)
    
    return [
        ConnectionResponse(
            id=c.id, name=c.name, host=c.host, port=c.port, 
            user=c.username, db_name=c.database_name, db_type=c.db_type, is_active=c.is_active,
            connection_status=c.connection_status, last_indexed_at=c.last_indexed_at, error_message=c.error_message
        )
        for c in connections
    ]

@router.post("", response_model=ConnectionResponse)
async def create_connection(
    req: ConnectionCreate,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    encrypted_pw = fernet.encrypt(req.password.encode()).decode()
    
    new_conn = DBConnection(
        tenant_id=tenant_id,
        name=req.name,
        host=req.host,
        port=req.port,
        username=req.user,
        encrypted_password=encrypted_pw,
        database_name=req.db_name,
        db_type=req.db_type,
        is_active=True
    )
    
    db.add(new_conn)
    await db.commit()
    await db.refresh(new_conn)
    
    return ConnectionResponse(
        id=new_conn.id, name=new_conn.name, host=new_conn.host, port=new_conn.port, 
        user=new_conn.username, db_name=new_conn.database_name, db_type=new_conn.db_type, is_active=new_conn.is_active,
        connection_status=new_conn.connection_status, last_indexed_at=new_conn.last_indexed_at, error_message=new_conn.error_message
    )

@router.post("/{connection_id}/reindex")
async def reindex_connection(
    connection_id: int,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    connections = await tenant_manager.get_tenant_connections(db, tenant_id)
    
    conn = next((c for c in connections if c.id == connection_id), None)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    from ..core.queue_manager import queue_manager
    from sqlalchemy import update
    
    # Mark as pending immediately
    stmt = update(DBConnection).where(DBConnection.id == connection_id).values(connection_status="pending", error_message=None)
    await db.execute(stmt)
    await db.commit()
    
    await queue_manager.enqueue_scan(tenant_id, connection_id)
    
    from ..services.cache_service import cache_service
    await cache_service.clear_all()
    
    return {"message": "Re-indexing queued"}

@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: int,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    connections = await tenant_manager.get_tenant_connections(db, tenant_id)
    
    conn = next((c for c in connections if c.id == connection_id), None)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    from sqlalchemy import delete
    await db.execute(delete(DBConnection).where(DBConnection.id == connection_id, DBConnection.tenant_id == tenant_id))
    await db.commit()
    return {"message": "Connection deleted"}
