import asyncio
import time
from app.agents.router_agent import router_agent
from app.agents.schema_retrieval_agent import schema_retrieval_agent
from app.agents.dashboard_chart_agent import dashboard_chart_agent
from app.core.config import settings
from cryptography.fernet import Fernet

async def test_dashboard(query):
    start = time.time()
    print(f"Testing: {query}")
    
    tenant_id = 1
    host = "100.86.181.18"
    port = 3317
    user = "root"
    password = "Cor3@369"
    db_name = "btggasify_purchase_live"
    db_conn_id = 10
    
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    encrypted_pw = fernet.encrypt(password.encode()).decode()

    module, intent_keywords = await router_agent.route_intent(query)
    schema_context_str = await schema_retrieval_agent.retrieve_schema_context(tenant_id, module, intent_keywords)
    data = await dashboard_chart_agent.generate_dashboard_data(
        query, schema_context_str, db_conn_id, host, port, user, encrypted_pw, db_name
    )
    
    duration = time.time() - start
    print(f"Time: {duration:.2f}s")
    print(f"Result Title: {data.get('title')}")
    print(f"Result Type: {data.get('chartType')}")
    print(f"Result Labels: {data.get('data', {}).get('labels')[:5] if data.get('data') else []}")
    print("-" * 50)

async def main():
    await test_dashboard("What is the PR to PO conversion trend?")
    await test_dashboard("Show active purchase orders")

asyncio.run(main())
