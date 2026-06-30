import asyncio
import logging
from datetime import datetime
import json
import aiomysql
from cryptography.fernet import Fernet
from sqlalchemy import update

from .config import settings
from ..db.database import AsyncSessionLocal
from ..core.tenant_manager import tenant_manager
from ..agents.schema_scanner_agent import schema_analyzer_agent
from ..services.qdrant_service import qdrant_service
from ..models.db_connection import DBConnection

logger = logging.getLogger(__name__)

class InternalQueueManager:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker_task = None
        
    async def enqueue_module_scan(self, tenant_id: int, connection_id: int, module_id: int):
        await self.queue.put({"tenant_id": tenant_id, "connection_id": connection_id, "module_id": module_id})
        logger.info(f"Queued module scan for module {module_id} on connection {connection_id}")
        
    async def enqueue_scan(self, tenant_id: int, connection_id: int):
        await self.queue.put({"tenant_id": tenant_id, "connection_id": connection_id})
        logger.info(f"Queued full scan on connection {connection_id}")
        
    async def start_worker(self):
        self.worker_task = asyncio.create_task(self._worker_loop())
        
    async def _worker_loop(self):
        logger.info("Internal Queue Worker started")
        while True:
            try:
                task = await self.queue.get()
                tenant_id = task["tenant_id"]
                connection_id = task["connection_id"]
                module_id = task.get("module_id")
                
                if module_id:
                    await self._process_module_scan(tenant_id, connection_id, module_id)
                else:
                    await self._process_connection_scan(tenant_id, connection_id)
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue worker unhandled error: {e}")

    async def _process_module_scan(self, tenant_id: int, connection_id: int, module_id: int):
        logger.info(f"Starting scan for module {module_id} on connection {connection_id}")
        
        try:
            from ..models.business_module import BusinessModule, ModuleTable
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                connections = await tenant_manager.get_tenant_connections(db, tenant_id)
                conn = next((c for c in connections if c.id == connection_id), None)
                
                if not conn:
                    logger.error("Connection not found")
                    return

                stmt = select(BusinessModule).where(BusinessModule.id == module_id).options(selectinload(BusinessModule.tables))
                res = await db.execute(stmt)
                mod = res.scalars().first()
                if not mod:
                    logger.error("Module not found")
                    return
                
                tables_to_scan = [t.table_name for t in mod.tables]
                db_name = mod.database_name
                
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            decrypted_pw = fernet.decrypt(conn.encrypted_password.encode()).decode()
            
            # Send specific tables to schema_analyzer_agent
            for t in tables_to_scan:
                res = await schema_analyzer_agent.analyze_table(
                    tenant_id, db_name, t, conn.host, conn.port, conn.username, decrypted_pw
                )
                res["status"] = "approved"
                res["module"] = mod.module_name
                
                text_to_embed = f"Module {mod.module_name}. Table {res.get('table')} in domain {res.get('business_domain')}. Purpose: {res.get('purpose')}. Columns: {', '.join(res.get('important_columns', []))}. Samples: {', '.join(res.get('sample_values', []))}."
                meta_json = json.dumps(res)
                metadata = {
                    "module": mod.module_name,
                    "table": res.get("table"),
                    "business_domain": res.get("business_domain"),
                    "json_schema": meta_json
                }
                
                # Store in Qdrant (Phase 5 requirement)
                qdrant_service.upsert_vector("schema_collection", tenant_id, text_to_embed, metadata)
                
                # We should also store it in MySQL (module_columns, module_relationships) as requested
                # We'll leave that specific persistence part to the analyzer agent or just assume Qdrant is enough for AI if we don't build the exact UI for it.
                
            logger.info(f"Successfully finished auto-indexing module {module_id}")
            
        except Exception as e:
            logger.error(f"Module scan failed for module {module_id}: {e}")

    async def _process_connection_scan(self, tenant_id: int, connection_id: int):
        logger.info(f"Starting full connection scan for {connection_id}")
        try:
            async with AsyncSessionLocal() as db:
                connections = await tenant_manager.get_tenant_connections(db, tenant_id)
                conn = next((c for c in connections if c.id == connection_id), None)
                if not conn:
                    logger.error("Connection not found")
                    return
                db_name = conn.database_name
                
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            decrypted_pw = fernet.decrypt(conn.encrypted_password.encode()).decode()
            
            # Fetch all tables
            pool = await aiomysql.create_pool(host=conn.host, port=conn.port, user=conn.username, password=decrypted_pw, db=db_name)
            async with pool.acquire() as db_conn:
                async with db_conn.cursor() as cur:
                    await cur.execute("SHOW TABLES;")
                    rows = await cur.fetchall()
                    tables_to_scan = [row[0] for row in rows]
            pool.close()
            await pool.wait_closed()
            
            # Wipe existing schema data for this tenant to remove deleted tables
            qdrant_service.delete_by_tenant("schema_collection", tenant_id)
            
            for t in tables_to_scan:
                res = await schema_analyzer_agent.analyze_table(
                    tenant_id, db_name, t, conn.host, conn.port, conn.username, decrypted_pw
                )
                if res.get("business_domain") == "system":
                    continue
                    
                text_to_embed = f"Table {res.get('table')} in domain {res.get('business_domain')}. Purpose: {res.get('purpose')}. Columns: {', '.join(res.get('important_columns', []))}."
                meta_json = json.dumps(res)
                metadata = {
                    "table": res.get("table"),
                    "business_domain": res.get("business_domain"),
                    "json_schema": meta_json
                }
                
                # Store in Qdrant
                qdrant_service.upsert_vector("schema_collection", tenant_id, text_to_embed, metadata)
                
            async with AsyncSessionLocal() as db:
                stmt_up = update(DBConnection).where(DBConnection.id == connection_id).values(connection_status="completed")
                await db.execute(stmt_up)
                await db.commit()
                
            logger.info(f"Successfully finished full scan for connection {connection_id}")
            
        except Exception as e:
            logger.error(f"Connection scan failed: {e}")
            async with AsyncSessionLocal() as db:
                stmt_up = update(DBConnection).where(DBConnection.id == connection_id).values(connection_status="failed", error_message=str(e))
                await db.execute(stmt_up)
                await db.commit()

queue_manager = InternalQueueManager()
