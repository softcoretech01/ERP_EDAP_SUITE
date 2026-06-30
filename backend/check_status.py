import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def check_status():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT id, name, database_name, connection_status, error_message FROM db_connections;'))
        print(result.fetchall())

asyncio.run(check_status())
