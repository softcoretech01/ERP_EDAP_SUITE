import asyncio
import aiomysql
from cryptography.fernet import Fernet
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.db_connection import DBConnection
from sqlalchemy import select

async def main():
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DBConnection).where(DBConnection.id == 10))
        conn = result.scalars().first()
    
    decrypted_pw = fernet.decrypt(conn.encrypted_password.encode()).decode()
    pool = await aiomysql.create_pool(host=conn.host, port=conn.port, user=conn.username, password=decrypted_pw, db=conn.database_name)
    async with pool.acquire() as dbconn:
        async with dbconn.cursor() as cur:
            await cur.execute("SHOW TABLES LIKE '%purchase%';")
            rows = await cur.fetchall()
            print('TABLES:', rows)
            
            await cur.execute("SHOW TABLES LIKE '%order%';")
            rows = await cur.fetchall()
            print('ORDER TABLES:', rows)
asyncio.run(main())
