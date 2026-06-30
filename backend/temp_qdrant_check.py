import os, sys
import asyncio

# Ensure backend path is in PYTHONPATH
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

from app.services.qdrant_service import qdrant_service

async def main():
    client = qdrant_service.client
    # List all collections
    collections = client.get_collections()
    print("Collections:", collections)
    # Get info for schema_collection
    try:
        info = client.get_collection("schema_collection")
        print("Schema collection info:", info)
    except Exception as e:
        print("Error getting schema collection info:", e)
    # Count vectors in schema_collection
    try:
        count = client.count(collection_name="schema_collection")
        print("Schema collection count:", count)
    except Exception as e:
        print("Error counting schema collection:", e)

if __name__ == "__main__":
    asyncio.run(main())
