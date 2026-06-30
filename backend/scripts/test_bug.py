import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.agents.agent_orchestrator import agent_orchestrator

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

from app.services.cache_service import cache_service

async def test():
    await cache_service.clear_all()
    async with AsyncSessionLocal() as db:
        query = "What is the total value of all active purchase orders"
        res = await agent_orchestrator.process_request(db, user_id=1, tenant_id=1, session_id="test_val", query=query, mode="db")
        print("FINAL RESPONSE:", res)

asyncio.run(test())
