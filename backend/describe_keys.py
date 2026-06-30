import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from app.core.config import settings
import aiomysql

async def test():
    pool = await aiomysql.create_pool(host=settings.DB_HOST, port=settings.DB_PORT, user=settings.DB_USER, password=settings.DB_PASSWORD, db='btggasify_purchase_live')
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            tables = ['tbl_PurchaseRequisition_Header', 'tbl_purchaseorder_header', 'tbl_grn_header', 'tbl_IRNReceipt_detail']
            for t in tables:
                print(f"--- {t} ---")
                await cur.execute(f"DESCRIBE {t}")
                for r in await cur.fetchall():
                    print(r[0])
                    
    pool_f = await aiomysql.create_pool(host=settings.DB_HOST, port=settings.DB_PORT, user=settings.DB_USER, password=settings.DB_PASSWORD, db='btggasify_finance_live')
    async with pool_f.acquire() as conn:
        async with conn.cursor() as cur:
            tables = ['tbl_accounts_payable', 'ApprovalRequests']
            for t in tables:
                print(f"--- {t} ---")
                await cur.execute(f"DESCRIBE {t}")
                for r in await cur.fetchall():
                    print(r[0])

asyncio.run(test())
