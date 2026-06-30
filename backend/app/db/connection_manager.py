from typing import Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from cryptography.fernet import Fernet
from ..core.config import settings

fernet = Fernet(settings.ENCRYPTION_KEY.encode())

class ConnectionManager:
    def __init__(self):
        # Cache async_sessionmakers to avoid recreating engines and to benefit from pooling
        self._session_makers: Dict[int, async_sessionmaker] = {}

    def get_database_url(self, host: str, port: int, user: str, encrypted_password: str, db_name: str) -> str:
        import urllib.parse
        password = fernet.decrypt(encrypted_password.encode()).decode()
        escaped_password = urllib.parse.quote_plus(password)
        return f"mysql+aiomysql://{user}:{escaped_password}@{host}:{port}/{db_name}"

    def get_session_maker(self, db_conn_id: int, host: str, port: int, user: str, encrypted_password: str, db_name: str) -> async_sessionmaker:
        if db_conn_id not in self._session_makers:
            url = self.get_database_url(host, port, user, encrypted_password, db_name)
            # Create a reusable engine for this specific ERP database
            engine = create_async_engine(url, pool_size=5, max_overflow=10, pool_pre_ping=True)
            self._session_makers[db_conn_id] = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
            
        return self._session_makers[db_conn_id]

    async def validate_connection(self, db_conn_id: int, host: str, port: int, user: str, encrypted_password: str, db_name: str) -> bool:
        try:
            session_maker = self.get_session_maker(db_conn_id, host, port, user, encrypted_password, db_name)
            async with session_maker() as session:
                # Test connection by executing a simple SELECT 1
                await session.execute(select(1))
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Database connection validation failed: {e}")
            return False

connection_manager = ConnectionManager()

