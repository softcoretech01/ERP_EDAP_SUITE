from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api import auth, chat, dashboard, connections, debug, customer_config
from .db.database import engine, Base

app = FastAPI(title="ERP AI Assistant V2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import time
import logging

logger = logging.getLogger("api_performance")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    # Avoid logging websocket upgrade noise if any
    if "api" in request.url.path:
        logger.info(f"PERF LOG: {request.method} {request.url.path} took {duration:.3f}s")
    return response

@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    if "Qdrant storage is locked by another process" in str(exc):
        return JSONResponse(
            status_code=503,
            content={"success": False, "message": "Qdrant storage is locked by another process"}
        )
    raise exc

@app.on_event("startup")
async def startup_event():
    # Initialize Qdrant singleton
    from .services.qdrant_service import init_qdrant, qdrant_service
    try:
        init_qdrant()
        # Validate collection dimensions and count
        qdrant_service.validate_qdrant()
    except Exception as e:
        print(f"Warning during Qdrant startup: {e}")

    # Launch Internal Queue Manager Worker
    import asyncio
    from .core.queue_manager import queue_manager
    asyncio.create_task(queue_manager.start_worker())

    # Recover any "scanning" jobs that died in a crash
    async def recover_jobs():
        from sqlalchemy import update
        async with engine.begin() as conn:
            from sqlalchemy import text as _text
            await conn.execute(_text("UPDATE db_connections SET connection_status='pending' WHERE connection_status='scanning'"))
    asyncio.create_task(recover_jobs())

    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure required columns exist (add if missing) using SQLAlchemy inspector
        try:
            def _ensure_database_schema(sync_conn):
                from sqlalchemy import inspect, text as _text
                insp = inspect(sync_conn)
                
                # Check users
                cols_users = [c['name'] for c in insp.get_columns('users')]
                if 'hashed_password' not in cols_users:
                    sync_conn.execute(_text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255)"))
                    print("Added missing column 'hashed_password' to users table")
                if 'full_name' not in cols_users:
                    sync_conn.execute(_text("ALTER TABLE users ADD COLUMN full_name VARCHAR(255) NULL"))
                    print("Added missing column 'full_name' to users table")
                if 'is_active' not in cols_users:
                    sync_conn.execute(_text("ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1"))
                    print("Added missing column 'is_active' to users table")
                if 'tenant_id' not in cols_users:
                    sync_conn.execute(_text("ALTER TABLE users ADD COLUMN tenant_id INT DEFAULT 1 NOT NULL"))
                    print("Added missing column 'tenant_id' to users table")

                # Check db_connections
                if 'db_connections' in insp.get_table_names():
                    cols_conn = [c['name'] for c in insp.get_columns('db_connections')]
                    if 'tenant_id' not in cols_conn:
                        sync_conn.execute(_text("ALTER TABLE db_connections ADD COLUMN tenant_id INT DEFAULT 1 NOT NULL"))
                        print("Added missing column 'tenant_id' to db_connections table")
                    if 'db_type' not in cols_conn:
                        sync_conn.execute(_text("ALTER TABLE db_connections ADD COLUMN db_type VARCHAR(50) DEFAULT 'mysql' NOT NULL"))
                        print("Added missing column 'db_type' to db_connections table")
                    if 'connection_status' not in cols_conn:
                        sync_conn.execute(_text("ALTER TABLE db_connections ADD COLUMN connection_status VARCHAR(50) DEFAULT 'pending'"))
                        print("Added missing column 'connection_status' to db_connections table")
                    if 'last_indexed_at' not in cols_conn:
                        sync_conn.execute(_text("ALTER TABLE db_connections ADD COLUMN last_indexed_at VARCHAR(50) NULL"))
                        print("Added missing column 'last_indexed_at' to db_connections table")
                    if 'error_message' not in cols_conn:
                        sync_conn.execute(_text("ALTER TABLE db_connections ADD COLUMN error_message VARCHAR(1000) NULL"))
                        print("Added missing column 'error_message' to db_connections table")

            await conn.run_sync(_ensure_database_schema)
        except Exception as e:
            print(f"Warning: could not ensure columns: {e}")
        
    # Seed default connection if empty
    from sqlalchemy import select
    from .models.db_connection import DBConnection
    from .models.permission import Permission
    from .models.role import Role
    from .models.user import User
    from .db.database import AsyncSessionLocal
    from cryptography.fernet import Fernet
    from .core.config import settings
    from .auth.auth_service import get_password_hash

    async with AsyncSessionLocal() as session:
        try:
            from .services.relationship_graph import relationship_graph
            await relationship_graph.ensure_loaded(session)
            
            # Seed permissions
            permissions_to_seed = ["chat_access", "upload_access", "dashboard_access"]
            seeded_perms = []
            for perm_name in permissions_to_seed:
                stmt = select(Permission).where(Permission.name == perm_name)
                res = await session.execute(stmt)
                perm = res.scalars().first()
                if not perm:
                    perm = Permission(name=perm_name, description=f"Grants {perm_name}")
                    session.add(perm)
                seeded_perms.append(perm)
            await session.commit()
            
            # Seed Administrator role
            from sqlalchemy.orm import selectinload
            stmt = select(Role).where(Role.name == "Administrator").options(selectinload(Role.permissions))
            res = await session.execute(stmt)
            admin_role = res.scalars().first()
            if not admin_role:
                admin_role = Role(name="Administrator", description="System Administrator")
                session.add(admin_role)
                await session.commit()
                # Link permissions
                admin_role.permissions = seeded_perms
                await session.commit()
            else:
                # Ensure all seeded permissions are linked
                current_perm_names = {p.name for p in admin_role.permissions}
                missing_perms = [p for p in seeded_perms if p.name not in current_perm_names]
                if missing_perms:
                    admin_role.permissions.extend(missing_perms)
                    await session.commit()
                    print(f"Linked missing permissions to Administrator role: {[p.name for p in missing_perms]}")
            
            # Seed default user if empty
            from sqlalchemy.orm import selectinload
            stmt = select(User).where(User.username == "kabil@gmail.com").options(selectinload(User.roles))
            res = await session.execute(stmt)
            default_user = res.scalars().first()
            if not default_user:
                hashed = get_password_hash("password123")
                default_user = User(
                    username="kabil@gmail.com",
                    email="kabil@gmail.com",
                    hashed_password=hashed,
                    full_name="Kabilesh",
                    is_active=True,
                    tenant_id=1
                )
                session.add(default_user)
                await session.commit()
                # Assign role
                default_user.roles = [admin_role]
                await session.commit()
                print("Seeded default user kabil@gmail.com with Administrator role")
            else:
                updated = False
                if not default_user.full_name:
                    default_user.full_name = "Kabilesh"
                    updated = True
                if admin_role and admin_role not in default_user.roles:
                    default_user.roles.append(admin_role)
                    updated = True
                if updated:
                    await session.commit()
                    print("Updated existing user kabil@gmail.com with full_name and/or Administrator role")

            # Seed connections based on ERP core credentials
            from sqlalchemy import delete
            cleanup_names = ["Tradeware Live", "Energy matrix ERP", "EnergyMatrix MySQL Database", "Btggasify Live", "Btggasify Finance", "Btggasify Purchase", "Btggasify Master", "Btggasify Userpanel", "Live ERP Database"]
            for name in cleanup_names:
                cleanup_stmt = delete(DBConnection).where(DBConnection.name == name)
                await session.execute(cleanup_stmt)
            await session.commit()

            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            target_conns = [
                {
                    "name": "Btggasify ERP Server",
                    "host": "100.86.181.18",
                    "port": 3317,
                    "database_name": "btggasify_purchase_live",
                    "username": "root",
                    "password": "Cor3@369"
                }
            ]
            
            for conn_info in target_conns:
                stmt = select(DBConnection).where(DBConnection.name == conn_info["name"])
                res = await session.execute(stmt)
                db_conn = res.scalars().first()
                
                encrypted_pw = fernet.encrypt(conn_info["password"].encode()).decode()
                
                if not db_conn:
                    conn_obj = DBConnection(
                        name=conn_info["name"],
                        host=conn_info["host"],
                        port=conn_info["port"],
                        database_name=conn_info["database_name"],
                        username=conn_info["username"],
                        encrypted_password=encrypted_pw,
                        is_active=True,
                        tenant_id=1,
                        db_type="mysql"
                    )
                    session.add(conn_obj)
                    print(f"Successfully seeded DB connection: {conn_info['name']}")
                else:
                    try:
                        decrypted = fernet.decrypt(db_conn.encrypted_password.encode()).decode()
                        if (decrypted != conn_info["password"] or 
                            db_conn.host != conn_info["host"] or 
                            db_conn.port != conn_info["port"] or 
                            db_conn.database_name != conn_info["database_name"] or 
                            db_conn.username != conn_info["username"]):
                            raise ValueError("Details mismatch")
                    except Exception:
                        print(f"Updating and re-encrypting DB connection: {conn_info['name']}")
                        db_conn.host = conn_info["host"]
                        db_conn.port = conn_info["port"]
                        db_conn.database_name = conn_info["database_name"]
                        db_conn.username = conn_info["username"]
                        db_conn.encrypted_password = encrypted_pw
            await session.commit()
        except Exception as e:
            print(f"Error seeding DB: {e}")

    from .api import auth, chat, dashboard, connections, debug, customer_config

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(connections.router, prefix="/api/connections", tags=["Connections"])
from .api import modules
app.include_router(modules.router, prefix="/api/modules", tags=["Modules"])
app.include_router(debug.router, prefix="/api/debug", tags=["Debug"])  # include debug endpoint
app.include_router(customer_config.router, prefix="/api/config", tags=["Configuration"])

@app.get("/")
def read_root():
    return {"message": "Welcome to ERP AI Assistant V2 API"}
