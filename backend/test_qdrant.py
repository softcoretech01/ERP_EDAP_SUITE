import asyncio
from app.services.qdrant_service import qdrant_service

async def test():
    results = qdrant_service.search_vectors("schema_collection", 1, "purchaseorder_header", limit=5)
    for r in results:
        print(r)

if __name__ == "__main__":
    asyncio.run(test())
