import asyncio
from app.db.database import AsyncSessionLocal
from app.agents.modules.purchase_agent import purchase_agent

async def run():
    async with AsyncSessionLocal() as db:
        res = await purchase_agent.handle_query(db, 1, "Show me all purchase memos", "", ["purchase_agent"])
        print(res)

asyncio.run(run())
