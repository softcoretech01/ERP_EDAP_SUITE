import asyncio
import aiomysql

async def test_mysql():
    try:
        pool = await aiomysql.create_pool(host='100.86.181.18', port=3317, user='root', password='Cor3@369')
        print('Connected successfully!')
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SHOW DATABASES;")
                databases = await cur.fetchall()
                print("Databases:")
                for db in databases:
                    print(f"- {db[0]}")
                    
        pool.close()
        await pool.wait_closed()
    except Exception as e:
        print(f'Connection failed: {e}')

if __name__ == '__main__':
    asyncio.run(test_mysql())
