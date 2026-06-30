import asyncio
from app.services.qdrant_service import qdrant_service

async def test():
    results = qdrant_service.search_vectors(collection_name="schema_collection", tenant_id=1, query="purchase order", limit=100)
    print(f"Total results: {len(results)}")
    if results:
        print("First result keys:", results[0].keys())
        print("First result payload:", results[0])

asyncio.run(test())
