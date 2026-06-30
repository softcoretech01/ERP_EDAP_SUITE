import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..db.database import get_db
from ..auth.permissions import get_current_user_token
from ..core.tenant_manager import tenant_manager
from ..models.db_connection import DBConnection
from ..models.business_module import BusinessModule, ModuleTable

from ..services.schema_service import schema_service
from ..core.queue_manager import queue_manager

router = APIRouter()
logger = logging.getLogger(__name__)

class ModuleSaveRequest(BaseModel):
    module: str
    database_name: str
    db_conn_id: int
    tables: List[str]

@router.get("/tables")
async def get_available_tables(
    db_conn_id: int,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Real-time query to fetch available tables from the customer DB (for dropdowns).
    """
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    
    # Verify connection belongs to tenant
    stmt = select(DBConnection).where(DBConnection.id == db_conn_id, DBConnection.tenant_id == tenant_id, DBConnection.is_active == True)
    result = await db.execute(stmt)
    conn = result.scalars().first()
    
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        tables_by_db = await schema_service.get_tables_only(
            conn.host, conn.port, conn.username, conn.encrypted_password, conn.database_name
        )
        return {"tables_by_db": tables_by_db, "database_name": conn.database_name}
    except Exception as e:
        logger.error(f"Error fetching tables: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/config")
async def get_module_config(
    module: str,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    from sqlalchemy.orm import selectinload
    stmt = select(BusinessModule).where(
        BusinessModule.tenant_id == tenant_id,
        BusinessModule.module_name == module
    ).options(selectinload(BusinessModule.tables))
    result = await db.execute(stmt)
    mod = result.scalars().first()
    
    if not mod:
        return {"database_name": "", "tables": []}
        
    return {
        "database_name": mod.database_name,
        "tables": [t.table_name for t in mod.tables]
    }

@router.post("/save")
async def save_module_config(
    req: ModuleSaveRequest,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    
    # 1. Delete existing module config if exists
    stmt = select(BusinessModule).where(
        BusinessModule.tenant_id == tenant_id,
        BusinessModule.module_name == req.module,
        BusinessModule.database_name == req.database_name
    )
    result = await db.execute(stmt)
    existing_mod = result.scalars().first()
    
    if existing_mod:
        await db.delete(existing_mod)
        await db.commit()

    # 2. Save new config
    new_module = BusinessModule(
        tenant_id=tenant_id,
        module_name=req.module,
        database_name=req.database_name
    )
    db.add(new_module)
    await db.flush() # flush to get ID
    
    for tbl in req.tables:
        db.add(ModuleTable(module_id=new_module.id, table_name=tbl))
        
    await db.commit()
    await db.refresh(new_module)

    # 3. Trigger targeted background scan
    await queue_manager.enqueue_module_scan(tenant_id, req.db_conn_id, new_module.id)

    return {"message": "Module configuration saved and scan queued", "module_id": new_module.id}

@router.post("/inject_pr_schema")
async def inject_pr_schema():
    from app.services.embeddings_service import embeddings_service
    from app.services.qdrant_service import qdrant_service
    import json
    
    pr_rules_text = """
MODULE CONFIGURATION
Module Name: Purchase Requisition (PR)
Business Description: This module manages purchase requisitions. Header table contains master PR information. Detail table contains item-level PR information.

TABLE 1: tbl_PurchaseRequisition_Header
Columns: ID (Primary Key), PRNo, PRDate, RequestedBy, Status

TABLE 2: tbl_PurchaseRequisition_Detail
Columns: DetailID, ID (Foreign Key), ItemCode, ItemName, Quantity

RELATIONSHIPS:
tbl_PurchaseRequisition_Header.ID = tbl_PurchaseRequisition_Detail.ID

JOIN RULES:
INNER JOIN tbl_PurchaseRequisition_Detail D ON tbl_PurchaseRequisition_Header.ID = tbl_PurchaseRequisition_Detail.ID
"""
    emb = embeddings_service.embed_text(pr_rules_text)
    metadata = {
        "module": "Purchase",
        "table": "tbl_PurchaseRequisition_Header, tbl_PurchaseRequisition_Detail",
        "business_domain": "Purchase Requisition Workflow and Relationships",
        "json_schema": json.dumps({
            "database": "erp_db",
            "table": "tbl_PurchaseRequisition_Header",
            "purpose": "Master relationship rules for PR Header and Detail. ALWAYS use these explicit join rules.",
            "important_columns": ["ID", "PRNo", "PRDate", "RequestedBy", "Status", "DetailID", "ItemCode", "ItemName", "Quantity"],
            "relationships": pr_rules_text
        })
    }
    
    qdrant_service.upsert_vector(
        collection_name="schema_collection",
        tenant_id=1,
        text=pr_rules_text,
        metadata=metadata
    )
    return {"message": "Success"}
