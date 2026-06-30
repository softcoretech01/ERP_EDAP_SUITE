import asyncio
import logging
from app.db.database import AsyncSessionLocal, engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.services.schema_scanner import schema_scanner
from app.models.db_connection import DBConnection
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)

async def run_ingestion():
    async with AsyncSessionLocal() as system_db:
        # Get the first active tenant connection with a valid database
        stmt = select(DBConnection).where(DBConnection.database_name != "").where(DBConnection.database_name != None)
        result = await system_db.execute(stmt)
        conn = result.scalars().first()
        
        if not conn:
            print("No tenant database connections found. Cannot ingest schema.")
            return

        from cryptography.fernet import Fernet
        from app.core.config import settings
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(conn.encrypted_password.encode()).decode()

        print(f"Connecting to {conn.database_name} on {conn.host}:{conn.port}...")
        
        import aiomysql
        # We need an async_sessionmaker for the customer DB.
        # But schema_scanner actually builds the session internally in _scan_mysql, wait, no it takes session_maker
        # Let's create an async engine for the customer DB
        target_engine = aiomysql.create_pool(
            host=conn.host,
            port=conn.port,
            user=conn.username,
            password=decrypted_pw,
            db=conn.database_name
        )
        
        # Actually SchemaScanner `_scan_mysql` expects `session_maker` which it uses as:
        # `async with session_maker() as session: result = await session.execute(...)`
        # Let's build a proper SQLAlchemy async engine for the customer DB
        from sqlalchemy.ext.asyncio import create_async_engine
        import urllib.parse
        safe_pw = urllib.parse.quote_plus(decrypted_pw)
        target_db_url = f"mysql+aiomysql://{conn.username}:{safe_pw}@{conn.host}:{conn.port}/{conn.database_name}"
        customer_engine = create_async_engine(target_db_url)
        customer_session_maker = async_sessionmaker(customer_engine, expire_on_commit=False)
        
        print("Running Schema Scanner & Persisting...")
        try:
            catalog = await schema_scanner.scan_and_persist_schema(
                system_db=system_db,
                target_session_maker=customer_session_maker,
                tenant_id=conn.tenant_id,
                db_type=conn.db_type,
                db_name=conn.database_name
            )
            print(f"Successfully ingested {len(catalog)} tables into MySQL metadata tables.")
        except Exception as e:
            print(f"Ingestion failed: {e}")
            import traceback
            traceback.print_exc()
        
        await customer_engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_ingestion())
