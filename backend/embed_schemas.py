import asyncio
import logging
from app.db.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.db_connection import DBConnection
from app.services.schema_enricher import schema_enricher
from app.services.qdrant_service import qdrant_service

logging.basicConfig(level=logging.INFO)

async def run_embedding():
    async with AsyncSessionLocal() as system_db:
        stmt = select(DBConnection).where(DBConnection.database_name != "").where(DBConnection.database_name != None)
        result = await system_db.execute(stmt)
        conn = result.scalars().first()
        
        if not conn:
            print("No tenant database connections found. Cannot embed schema.")
            return

        print(f"Enriching tables for {conn.database_name}...")
        payloads = await schema_enricher.enrich_schema(system_db, conn.tenant_id, conn.database_name)
        
        if not payloads:
            print("No payloads generated. Did you run ingest_schema.py first?")
            return

        print(f"Embedding {len(payloads)} payloads into Qdrant...")
        
        # Initialize or recreate collections if dimensions changed
        qdrant_service.init_collections()
        
        # Clear existing tenant data before embedding to avoid duplicates
        qdrant_service.delete_by_tenant("schema_collection", conn.tenant_id)
        
        for payload in payloads:
            import json
            text_to_embed = f"Table {payload['table_name']}. Business Name: {payload['business_name']}. Description: {payload['description']}. Keywords: {', '.join(payload['keywords'])}. Columns: {', '.join(payload['columns'])}"
            
            qdrant_service.upsert_vector(
                collection_name="schema_collection",
                tenant_id=conn.tenant_id,
                text=text_to_embed,
                metadata=payload
            )
            
        print("Embedding complete!")
        qdrant_service.validate_qdrant()

if __name__ == "__main__":
    asyncio.run(run_embedding())
