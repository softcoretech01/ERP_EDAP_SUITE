import asyncio
import aiomysql

async def f():
    pool = await aiomysql.create_pool(host='100.86.181.18',port=3317,user='root',password='Cor3@369',db='btggasify_purchase_live')
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DESCRIBE tbl_purchaseorder_header')
            rows = await cur.fetchall()
            print([r[0] for r in rows])
    pool.close()
    await pool.wait_closed()

asyncio.run(f())
