import asyncio
import logging
import json
import aiomysql
from cryptography.fernet import Fernet

from .config import settings
from ..db.database import AsyncSessionLocal
from ..core.tenant_manager import tenant_manager
from ..agents.schema_scanner_agent import schema_analyzer_agent
from ..services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

async def auto_seed_schemas():
    """Background task to scan and auto-index schemas if Qdrant is empty."""
    try:
        # Wait a few seconds to let Uvicorn fully start up
        await asyncio.sleep(5)
        
        qdrant_service.init_collections()
        
        try:
            count_result = qdrant_service.client.count("schema_collection")
            if count_result.count > 0:
                logger.info(f"Auto-Indexer: Qdrant already contains {count_result.count} schemas. Skipping auto-scan.")
                return
        except Exception as e:
            logger.warning(f"Auto-Indexer: Could not count schemas (might be empty): {e}")
            
        logger.info("Auto-Indexer: Qdrant 'schema_collection' is empty. Starting auto-scan of database tables...")
        
        tenant_id = 1
        async with AsyncSessionLocal() as db:
            connections = await tenant_manager.get_tenant_connections(db, tenant_id)
            if not connections:
                logger.warning("Auto-Indexer: No active database connections found for tenant 1.")
                return
                
            conn = connections[0]
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            decrypted_pw = fernet.decrypt(conn.encrypted_password.encode()).decode()
            
            # Fetch all tables
            tables = []
            try:
                pool = await aiomysql.create_pool(
                    host=conn.host, 
                    port=conn.port, 
                    user=conn.username, 
                    password=decrypted_pw
                )
                async with pool.acquire() as db_conn:
                    async with db_conn.cursor() as cur:
                        await cur.execute("SHOW DATABASES;")
                        dbs = await cur.fetchall()
                        for db_tuple in dbs:
                            db_name = db_tuple[0]
                            if db_name.lower() in ['information_schema', 'mysql', 'performance_schema', 'sys']:
                                continue
                            
                            await cur.execute(f"SHOW TABLES FROM `{db_name}`;")
                            res = await cur.fetchall()
                            for t in res:
                                tables.append((db_name, t[0]))
                pool.close()
                await pool.wait_closed()
            except Exception as e:
                logger.error(f"Auto-Indexer: Failed to fetch tables: {e}")
                return
                
            if not tables:
                logger.warning("Auto-Indexer: No tables found to scan.")
                return
                
            logger.info(f"Auto-Indexer: Found {len(tables)} tables. Scanning and indexing...")
            
            indexed_count = 0
            for db_name, t in tables:
                try:
                    res = await schema_analyzer_agent.analyze_table(
                        tenant_id, db_name, t,
                        conn.host, conn.port, 
                        conn.username, decrypted_pw
                    )
                    res["status"] = "approved"
                    
                    text_to_embed = f"Table {res.get('table')} in domain {res.get('business_domain')}. Purpose: {res.get('purpose')}. Columns: {', '.join(res.get('important_columns', []))}. Samples: {', '.join(res.get('sample_values', []))}."
                    meta_json = json.dumps(res)
                    metadata = {
                        "table": res.get("table"),
                        "business_domain": res.get("business_domain"),
                        "json_schema": meta_json
                    }
                    
                    qdrant_service.upsert_vector("schema_collection", tenant_id, text_to_embed, metadata)
                    indexed_count += 1
                    if indexed_count % 10 == 0:
                        logger.info(f"Auto-Indexer: Indexed {indexed_count}/{len(tables)} tables...")
                        
                except Exception as e:
                    logger.error(f"Auto-Indexer: Error processing table {db_name}.{t}: {e}")
                    
            logger.info(f"Auto-Indexer: Successfully finished auto-indexing {indexed_count} schemas.")
            
    except Exception as e:
        logger.error(f"Auto-Indexer: Unhandled exception during auto-seed: {e}")
