import asyncio
from app.agents.sql_agent import sql_agent
from app.db.database import get_db
from app.models.db_connection import DBConnection
from sqlalchemy.future import select
from cryptography.fernet import Fernet
from app.core.config import settings

async def test():
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    
    async for db in get_db():
        stmt = select(DBConnection).where(DBConnection.id == 1)
        result = await db.execute(stmt)
        conn = result.scalar_one_or_none()
        
        if conn:
            pw = fernet.decrypt(conn.encrypted_password.encode()).decode()
            
            with open("temp_output.txt", "w") as f:
                f.write("--- PR TABLE RAW CHECK ---\n")
                
                rows = await sql_agent.execute_sql_raw(conn.host, conn.port, conn.username, pw, conn.database_name, "SELECT COUNT(*) as TotalPRs FROM tbl_PurchaseRequisition_Header;")
                f.write(f"Total PRs: {rows}\n")
                
                rows = await sql_agent.execute_sql_raw(conn.host, conn.port, conn.username, pw, conn.database_name, "SELECT COUNT(*) as NotUtilized FROM tbl_PurchaseRequisition_Header WHERE IsPOUtil = 0;")
                f.write(f"IsPOUtil = 0: {rows}\n")
                
                rows = await sql_agent.execute_sql_raw(conn.host, conn.port, conn.username, pw, conn.database_name, "SELECT COUNT(*) as NullUtilized FROM tbl_PurchaseRequisition_Header WHERE IsPOUtil IS NULL;")
                f.write(f"IsPOUtil IS NULL: {rows}\n")
                
        break

asyncio.run(test())
