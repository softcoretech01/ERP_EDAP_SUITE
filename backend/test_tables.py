import asyncio
import aiomysql

async def main():
    pool = await aiomysql.create_pool(host='100.86.181.18', port=3317, user='root', password='Cor3@369', db='btggasify_purchase_live')
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SHOW TABLES;")
            tables = await cur.fetchall()
            print("Tables in btggasify_purchase_live:")
            for t in tables:
                print(t[0])
    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
