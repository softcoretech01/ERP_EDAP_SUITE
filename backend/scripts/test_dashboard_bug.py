import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

from app.models.db_connection import DBConnection
from sqlalchemy.future import select

from app.agents.router_agent import router_agent
from app.agents.schema_retrieval_agent import schema_retrieval_agent
from app.agents.dashboard_chart_agent import dashboard_chart_agent
from app.services.cache_service import cache_service

async def test():
    await cache_service.clear_all()
    async with AsyncSessionLocal() as db:
        stmt = select(DBConnection).where(DBConnection.id == 1)
        result = await db.execute(stmt)
        conn_record = result.scalar_one_or_none()
        
        if not conn_record:
            print("No connection record found.")
            return

        query = "Which PRs have not yet become Purchase Orders"
        
        module, intent_keywords = await router_agent.route_intent(query)
        schema_context_str = await schema_retrieval_agent.retrieve_schema_context(conn_record.tenant_id, module, intent_keywords)
        
        print("--- SCHEMA CONTEXT ---")
        print(schema_context_str)
        print("----------------------")
        
        data = await dashboard_chart_agent.generate_dashboard_data(
            query, 
            schema_context_str, 
            conn_record.id, 
            conn_record.host, 
            conn_record.port, 
            conn_record.username, 
            conn_record.encrypted_password, 
            conn_record.database_name
        )
        
        import json
        print("\n--- DASHBOARD DATA ---")
        print(json.dumps(data, indent=2))

asyncio.run(test())
