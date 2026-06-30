from typing import Dict, List, Any
from ..db.connection_manager import connection_manager
from sqlalchemy import text

class SchemaService:
    def __init__(self):
        # Cache per database connection id
        self._schema_cache: Dict[int, Dict[str, Any]] = {}

    async def extract_schema(self, db_conn_id: int, host: str, port: int, user: str, encrypted_password: str, db_name: str) -> Dict[str, Any]:
        if db_conn_id in self._schema_cache:
            return self._schema_cache[db_conn_id]
            
        session_maker = connection_manager.get_session_maker(db_conn_id, host, port, user, encrypted_password, db_name)
        schema_catalog = {}
        
        async with session_maker() as session:
            if db_name:
                query = text("""
                    SELECT TABLE_NAME, COLUMN_NAME, TABLE_SCHEMA
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = :db_name
                """)
                result = await session.execute(query, {"db_name": db_name})
            else:
                query = text("""
                    SELECT TABLE_NAME, COLUMN_NAME, TABLE_SCHEMA
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                """)
                result = await session.execute(query)
            
            for row in result.fetchall():
                table = row[0]
                column = row[1]
                schema_name = row[2]
                
                table_key = table if db_name else f"`{schema_name}`.`{table}`"
                
                if table_key not in schema_catalog:
                    schema_catalog[table_key] = {
                        "table": table_key,
                        "columns": []
                    }
                schema_catalog[table_key]["columns"].append(column)
                
        self._schema_cache[db_conn_id] = schema_catalog
        return schema_catalog

    async def get_tables_only(self, host: str, port: int, user: str, encrypted_password: str, db_name: str) -> Dict[str, List[str]]:
        from cryptography.fernet import Fernet
        from ..core.config import settings
        import aiomysql
        
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted_pw = fernet.decrypt(encrypted_password.encode()).decode()
        
        tables_by_db = {}
        try:
            pool = await aiomysql.create_pool(
                host=host, port=port, user=user, password=decrypted_pw, db=db_name if db_name else None
            )
            async with pool.acquire() as db_conn:
                async with db_conn.cursor() as cur:
                    if db_name:
                        await cur.execute("SHOW TABLES;")
                        res = await cur.fetchall()
                        tables_by_db[db_name] = [t[0] for t in res]
                    else:
                        await cur.execute("SHOW DATABASES;")
                        dbs = await cur.fetchall()
                        for db_tuple in dbs:
                            d = db_tuple[0]
                            if d.lower() in ['information_schema', 'mysql', 'performance_schema', 'sys']:
                                continue
                            await cur.execute(f"SHOW TABLES FROM `{d}`;")
                            res = await cur.fetchall()
                            tables_by_db[d] = [t[0] for t in res]
            pool.close()
            await pool.wait_closed()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error fetching tables: {e}")
            raise e
            
        return tables_by_db

schema_service = SchemaService()
