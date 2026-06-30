import asyncio
import aiomysql
from cryptography.fernet import Fernet
from app.core.config import settings

async def run():
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    # from debug.log we know user is erp_user and db is erp_db
    # wait, I don't know the exact encrypted password here. I'll just check what the user is experiencing.
    pass
