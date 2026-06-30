import asyncio
import uuid
import time
import logging
from app.db.database import AsyncSessionLocal
from app.agents.agent_orchestrator import agent_orchestrator

logging.basicConfig(level=logging.INFO)

async def test_single_query():
    query = "list items and customer"
    session_id = str(uuid.uuid4())
    
    print(f"Testing AI with query: '{query}'")
    
    async with AsyncSessionLocal() as db:
        start_time = time.time()
        try:
            response = await agent_orchestrator.process_request(
                db=db,
                user_id=1,
                tenant_id=1,
                session_id=session_id,
                query=query
            )
            elapsed = time.time() - start_time
            print(f"AI Response:\n{response}\n")
            print(f"[Speed: {elapsed:.2f} seconds]")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Error occurred: {e}")
            print(f"[Speed: {elapsed:.2f} seconds]")

if __name__ == "__main__":
    asyncio.run(test_single_query())
