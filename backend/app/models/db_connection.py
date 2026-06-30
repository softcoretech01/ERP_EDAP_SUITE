from sqlalchemy import Column, Integer, String, Boolean
from ..db.database import Base

class DBConnection(Base):
    __tablename__ = "db_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=3306)
    database_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(Integer, default=1, index=True, nullable=False)
    db_type = Column(String(50), default="mysql", nullable=False)
    
    connection_status = Column(String(50), default="pending")
    last_indexed_at = Column(String(50), nullable=True)
    error_message = Column(String(1000), nullable=True)
