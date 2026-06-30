import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.db_connection import DBConnection
from app.agents.router_agent import router_agent
from app.agents.schema_retrieval_agent import schema_retrieval_agent
from app.agents.dashboard_chart_agent import dashboard_chart_agent
from app.services.synonym_service import synonym_service

queries = [
    "What is our total procurement spend for this month?",
    "Who are our top 5 suppliers by total order value?",
    "What is the status distribution of all purchase orders?",
    "Show me the trend of daily purchase order creations over the last 30 days.",
    "List all purchase orders created today."
]

async def run_tests():
    async with AsyncSessionLocal() as session:
        # Load synonyms explicitly for local run
        await synonym_service.load_synonyms(session)
        
        from app.services.relationship_graph import relationship_graph
        await relationship_graph.ensure_loaded(session)
        
        # Get connection
        stmt = select(DBConnection).where(DBConnection.name == "Btggasify ERP Server")
        res = await session.execute(stmt)
        conn = res.scalars().first()
        
        if not conn:
            print("No connection found")
            return
            
        for idx, q in enumerate(queries, 1):
            print(f"\n{'='*50}\nTEST {idx}: {q}\n{'='*50}")
            
            # 1. Route
            module, keywords = await router_agent.route_intent(q)
            print(f"Module: {module}, Keywords: {keywords}")
            
            # 2. Retrieve Schema
            schema_context = await schema_retrieval_agent.retrieve_schema_context(conn.tenant_id, module, keywords)
            
            # 3. Add explicit mapping hints
            mapping_hints = await synonym_service.augment_query(q, module, schema_context)
            
            # 4. Generate Dashboard Data
            data = await dashboard_chart_agent.generate_dashboard_data(
                query=q,
                schema_context_str=schema_context,
                db_conn_id=conn.id,
                host=conn.host,
                port=conn.port,
                user=conn.username,
                encrypted_password=conn.encrypted_password,
                db_name=conn.database_name,
                mapping_hints=mapping_hints
            )
            
            print("\nRESULT:")
            print(json.dumps(data, indent=2))
            
if __name__ == "__main__":
    asyncio.run(run_tests())
