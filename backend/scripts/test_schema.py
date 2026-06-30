import asyncio
import sys
from app.agents.schema_retrieval_agent import schema_retrieval_agent

from app.services.cache_service import cache_service

async def test():
    await cache_service.clear_all()
    # Attempt to retrieve schema context for purchase orders
    context = await schema_retrieval_agent.retrieve_schema_context(tenant_id=1, module="Purchase", intent_keywords="purchase order created this month")
    
    print("=== SCHEMA CONTEXT ===")
    print(context)
    print("======================")

asyncio.run(test())
