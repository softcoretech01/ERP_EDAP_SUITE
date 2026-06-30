import asyncio
from app.services.qdrant_service import qdrant_service
from app.services.embeddings_service import embeddings_service
from app.models.business_module import BusinessModule
from app.db.database import AsyncSessionLocal
from sqlalchemy import select
import json

async def inject_pr_rules():
    tenant_id = 1
    
    # Text provided by user
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
    
    print("Generating embedding for PR rules...")
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
    
    print("Inserting into Qdrant schema_collection...")
    await qdrant_service.upsert_vector(
        collection_name="schema_collection",
        tenant_id=tenant_id,
        text=pr_rules_text,
        metadata=metadata
    )
    print("Successfully injected PR relationship rules into AI Memory!")

if __name__ == "__main__":
    asyncio.run(inject_pr_rules())
