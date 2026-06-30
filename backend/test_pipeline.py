import asyncio
from app.db.database import AsyncSessionLocal
from app.models.schema_models import SchemaTable
from sqlalchemy import select
from app.agents.agent_orchestrator import agent_orchestrator

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(SchemaTable))
        tables = res.scalars().all()
        print(f"Total tables ingested in MySQL: {len(tables)}")
        if len(tables) > 0:
            print(f"Sample tables: {[t.table_name for t in tables[:5]]}")

        # Simulate a purchase query
        query = "Show me the 5 most recent purchase orders with their amounts."
        print(f"\n--- Testing Query ---")
        print(f"Query: {query}")
        
        # User ID 1, Tenant ID 1, Session ID 'test-session'
        try:
            response = await agent_orchestrator.process_request(
                db=db, 
                user_id=1, 
                tenant_id=1, 
                session_id="test-session-1", 
                query=query
            )
            print("\n--- Pipeline Response ---")
            print(response)
        except Exception as e:
            print(f"Error executing pipeline: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
