import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.db_connection import DBConnection
from sqlalchemy import select

async def run():
    engine = create_async_engine('mysql+aiomysql://root:Cor3@369@100.86.181.18:3317/btggasify_live')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(DBConnection))
        for r in result.scalars():
            print(f"ID: {r.id}, Host: {r.host}, DB: {r.database_name}, Tenant: {r.tenant_id}")

if __name__ == '__main__':
    asyncio.run(run())
