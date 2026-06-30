import asyncio
from app.agents.agent_orchestrator import agent_orchestrator
from app.db.database import AsyncSessionLocal

async def test():
    async with AsyncSessionLocal() as db:
        res = await agent_orchestrator.process_request(db, user_id=1, tenant_id=1, session_id='test-session-123', query='how many invoice are creted this year')
        print('=============================')
        print('RESULT:')
        print(res)
        print('=============================')

asyncio.run(test())
