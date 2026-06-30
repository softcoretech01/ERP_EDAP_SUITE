import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from app.services.qdrant_service import qdrant_service

def check_qdrant():
    res = qdrant_service.client.scroll(
        collection_name="schema_collection",
        limit=100
    )
    for point in res[0]:
        print(point.payload.get('table'), point.payload.get('tenant_id'))

check_qdrant()
