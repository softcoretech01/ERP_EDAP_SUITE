import asyncio
from app.services.qdrant_service import qdrant_service

async def run():
    res = qdrant_service.search_vectors("schema_collection", tenant_id=1, query="purchaseorder header", limit=5)
    for r in res:
        if "tbl_purchaseorder_header" in str(r).lower():
            print(f"Table: {r['table_name']}")
            print(f"Columns: {r['columns']}")

asyncio.run(run())
