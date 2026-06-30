import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from app.core.config import settings
import aiomysql

async def test():
    pool = await aiomysql.create_pool(host=settings.DB_HOST, port=settings.DB_PORT, user=settings.DB_USER, password=settings.DB_PASSWORD, db='btggasify_finance_live')
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SHOW TABLES')
            tables = [r[0] for r in await cur.fetchall()]
            for t in tables:
                print(t)

asyncio.run(test())
