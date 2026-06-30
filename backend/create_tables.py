import asyncio
from app.db.database import engine, Base
from app.models import *

async def run():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

if __name__ == '__main__':
    asyncio.run(run())
