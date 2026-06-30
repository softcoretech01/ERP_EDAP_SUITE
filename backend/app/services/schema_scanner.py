import logging
from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from ..models.schema_models import SchemaTable, SchemaColumn, SchemaRelationship

logger = logging.getLogger(__name__)

class SchemaScanner:
    async def scan_and_persist_schema(self, system_db: AsyncSession, target_session_maker: async_sessionmaker, tenant_id: int, db_type: str, db_name: str) -> Dict[str, Any]:
        schema_catalog = await self.scan_schema(target_session_maker, db_type, db_name)
        
        # Clear existing for this db_name
        from sqlalchemy import delete
        await system_db.execute(delete(SchemaTable).where(SchemaTable.database_name == db_name, SchemaTable.tenant_id == tenant_id))
        
        for table_name, table_info in schema_catalog.items():
            schema_table = SchemaTable(
                tenant_id=tenant_id,
                database_name=db_name,
                table_name=table_name,
                table_type=table_info.get("type", "table")
            )
            system_db.add(schema_table)
            await system_db.flush()  # To get the table ID
            
            for col in table_info.get("columns", []):
                schema_col = SchemaColumn(
                    table_id=schema_table.id,
                    column_name=col["name"],
                    data_type=str(col["data_type"]),
                    is_primary_key=col["primary_key"]
                )
                system_db.add(schema_col)
                
            for fk in table_info.get("foreign_keys", []):
                schema_rel = SchemaRelationship(
                    source_table=table_name,
                    source_column=fk["column"],
                    target_table=fk["referenced_table"],
                    target_column=fk["referenced_column"]
                )
                system_db.add(schema_rel)
                
        await system_db.commit()
        return schema_catalog

    async def scan_schema(self, session_maker: async_sessionmaker, db_type: str, db_name: str) -> Dict[str, Any]:
        dialect = db_type.lower()
        if "postgres" in dialect or "pg" in dialect:
            return await self._scan_postgresql(session_maker, db_name)
        else:
            return await self._scan_mysql(session_maker, db_name)

    async def _scan_mysql(self, session_maker: async_sessionmaker, db_name: str) -> Dict[str, Any]:
        schema_catalog = {}
        async with session_maker() as session:
            # 1. Get Tables and Views
            tbl_res = await session.execute(text("SHOW FULL TABLES"))
            tables = []
            for row in tbl_res.fetchall():
                name, tbl_type = row[0], row[1]
                tables.append({"name": name, "type": "view" if "VIEW" in tbl_type else "table"})
            
            # 2. Get Relationships (Foreign Keys)
            rel_query = """
                SELECT 
                    TABLE_NAME,
                    COLUMN_NAME, 
                    CONSTRAINT_NAME, 
                    REFERENCED_TABLE_NAME, 
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = :db_name AND REFERENCED_TABLE_NAME IS NOT NULL
            """
            rel_res = await session.execute(text(rel_query), {"db_name": db_name})
            relationships = {}
            for row in rel_res.fetchall():
                tbl, col, _, ref_tbl, ref_col = row
                if tbl not in relationships:
                    relationships[tbl] = []
                relationships[tbl].append({
                    "column": col,
                    "referenced_table": ref_tbl,
                    "referenced_column": ref_col
                })

            # 3. Get Columns, Types, PKs
            for tbl_info in tables:
                tbl_name = tbl_info["name"]
                col_query = """
                    SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :table_name
                """
                col_res = await session.execute(text(col_query), {"db_name": db_name, "table_name": tbl_name})
                
                columns_list = []
                pks = []
                for col_row in col_res.fetchall():
                    c_name, d_type, c_key, nullable, default, comment = col_row
                    is_pk = "PRI" in str(c_key).upper()
                    if is_pk:
                        pks.append(c_name)
                    
                    columns_list.append({
                        "name": c_name,
                        "data_type": d_type,
                        "primary_key": is_pk,
                        "nullable": nullable == "YES",
                        "default": default,
                        "comment": comment or ""
                    })

                schema_catalog[tbl_name] = {
                    "table": tbl_name,
                    "type": tbl_info["type"],
                    "columns": columns_list,
                    "primary_keys": pks,
                    "foreign_keys": relationships.get(tbl_name, [])
                }
                
        return schema_catalog

    async def _scan_postgresql(self, session_maker: async_sessionmaker, db_name: str) -> Dict[str, Any]:
        schema_catalog = {}
        async with session_maker() as session:
            # 1. Get Tables and Views (Postgres public schema)
            tbl_query = """
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
            tbl_res = await session.execute(text(tbl_query))
            tables = []
            for row in tbl_res.fetchall():
                name, tbl_type = row[0], row[1]
                tables.append({"name": name, "type": "view" if "VIEW" in tbl_type else "table"})
            
            # 2. Get Relationships (Foreign Keys) in Postgres
            rel_query = """
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS referenced_table_name,
                    ccu.column_name AS referenced_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            """
            rel_res = await session.execute(text(rel_query))
            relationships = {}
            for row in rel_res.fetchall():
                tbl, col, ref_tbl, ref_col = row
                if tbl not in relationships:
                    relationships[tbl] = []
                relationships[tbl].append({
                    "column": col,
                    "referenced_table": ref_tbl,
                    "referenced_column": ref_col
                })

            # 3. Get Columns, Types, PKs in Postgres
            for tbl_info in tables:
                tbl_name = tbl_info["name"]
                
                # Fetch PK columns
                pk_query = """
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = :table_name::regclass AND i.indisprimary
                """
                pks = []
                try:
                    pk_res = await session.execute(text(pk_query), {"table_name": tbl_name})
                    pks = [r[0] for r in pk_res.fetchall()]
                except Exception:
                    # Fallback / ignore if PG table isn't fully registered
                    pass
                
                col_query = """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :table_name
                """
                col_res = await session.execute(text(col_query), {"table_name": tbl_name})
                
                columns_list = []
                for col_row in col_res.fetchall():
                    c_name, d_type, nullable, default = col_row
                    is_pk = c_name in pks
                    
                    columns_list.append({
                        "name": c_name,
                        "data_type": d_type,
                        "primary_key": is_pk,
                        "nullable": nullable == "YES",
                        "default": str(default) if default is not None else "",
                        "comment": "" # Pg comments are stored in pg_description, keep empty for simplicity
                    })

                schema_catalog[tbl_name] = {
                    "table": tbl_name,
                    "type": tbl_info["type"],
                    "columns": columns_list,
                    "primary_keys": pks,
                    "foreign_keys": relationships.get(tbl_name, [])
                }
                
        return schema_catalog

schema_scanner = SchemaScanner()
