import asyncio
from app.agents.sql_agent import sql_agent
from cryptography.fernet import Fernet
from app.core.config import settings

async def run():
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    # Assuming connection string info from debug.log
    # Let's just execute a raw SQL using execute_sql_raw directly, wait, I need the encrypted password from DBConnection!
    # I can just fetch it using SQLAlchemy!
    from app.db.database import get_db
    from app.models.db_connection import DBConnection
    from sqlalchemy.future import select
    
    async for db in get_db():
        stmt = select(DBConnection).where(DBConnection.id == 1)
        result = await db.execute(stmt)
        conn = result.scalar_one_or_none()
        
        if conn:
            pw = fernet.decrypt(conn.encrypted_password.encode()).decode()
            rows = await sql_agent.execute_sql_raw(conn.host, conn.port, conn.username, pw, conn.database_name, "SELECT IsPOUtil, COUNT(*) FROM tbl_PurchaseRequisition_Header GROUP BY IsPOUtil;")
            print("IsPOUtil distribution:")
            for r in rows:
                print(r)
        break

if __name__ == "__main__":
    asyncio.run(run())
