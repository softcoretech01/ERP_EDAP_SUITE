import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from app.services.qdrant_service import qdrant_service

def inspect_qdrant():
    try:
        qdrant_service.init_collections()
        res = qdrant_service.client.scroll(
            collection_name="schema_collection",
            limit=100
        )
        print("Total points returned:", len(res[0]))
        for point in res[0]:
            print(f"ID: {point.id}, Table: {point.payload.get('table', 'UNKNOWN')} - {point.payload.get('table_name', 'UNKNOWN')}")
    except Exception as e:
        print("Error:", e)

inspect_qdrant()
