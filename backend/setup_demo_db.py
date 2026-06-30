import asyncio
from app.db.database import AsyncSessionLocal
from app.models.db_connection import DBConnection
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.core.config import settings

async def insert_demo_connection():
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    encrypted_pw = fernet.encrypt(b"Cor3@369").decode()

    async with AsyncSessionLocal() as session:
        # Check if exists
        stmt = select(DBConnection).where(DBConnection.tenant_id == 1, DBConnection.name == "Live ERP Database")
        result = await session.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            existing.host = "100.86.181.18"
            existing.port = 3317
            existing.username = "root"
            existing.encrypted_password = encrypted_pw
            existing.database_name = "btggasify_live"
            existing.db_type = "mysql"
            existing.is_active = True
            print("Updated existing connection.")
        else:
            new_conn = DBConnection(
                tenant_id=1,
                name="Live ERP Database",
                host="100.86.181.18",
                port=3317,
                username="root",
                encrypted_password=encrypted_pw,
                database_name="btggasify_live",
                db_type="mysql",
                is_active=True
            )
            session.add(new_conn)
            print("Created new connection.")
        
        await session.commit()
        print("Database connection successfully configured for Tenant 1.")

if __name__ == "__main__":
    asyncio.run(insert_demo_connection())
