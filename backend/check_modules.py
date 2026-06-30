import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def check_modules():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT * FROM module_tables WHERE table_name = "tbl_invoice_receiptnote_header";'))
        print("module_tables:", result.fetchall())

asyncio.run(check_modules())
