import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def get_synonyms():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text('SELECT base_term, synonyms FROM synonym_mappings'))
        print(res.fetchall())

asyncio.run(get_synonyms())
