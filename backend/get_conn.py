import asyncio
from app.db.database import AsyncSessionLocal
from app.core.tenant_manager import tenant_manager

async def main():
    async with AsyncSessionLocal() as db:
        conns = await tenant_manager.get_tenant_connections(db, 1)
        print("IDs:", [c.id for c in conns])

asyncio.run(main())
