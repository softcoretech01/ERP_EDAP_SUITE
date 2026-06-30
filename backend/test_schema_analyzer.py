import asyncio
from app.db.database import AsyncSessionLocal
from app.core.tenant_manager import tenant_manager
from cryptography.fernet import Fernet
from app.core.config import settings

async def main():
    async with AsyncSessionLocal() as db:
        conns = await tenant_manager.get_tenant_connections(db, 1)
        conn = conns[0]
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(conn.encrypted_password.encode()).decode()
        
        import aiomysql
        tables = []
        pool = await aiomysql.create_pool(
            host=conn.host, 
            port=conn.port, 
            user=conn.username, 
            password=decrypted_pw
        )
        async with pool.acquire() as db_conn:
            async with db_conn.cursor() as cur:
                await cur.execute("SHOW DATABASES;")
                dbs = await cur.fetchall()
                for db_tuple in dbs:
                    db_name = db_tuple[0]
                    if db_name.lower() in ['information_schema', 'mysql', 'performance_schema', 'sys']:
                        continue
                    
                    await cur.execute(f"SHOW TABLES FROM `{db_name}`;")
                    res = await cur.fetchall()
                    for t in res:
                        tables.append((db_name, t[0]))
        pool.close()
        await pool.wait_closed()
        print("Found tables:", tables)

asyncio.run(main())
