from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship as _relationship
from ..db.database import Base

class BusinessModule(Base):
    __tablename__ = "business_modules"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    module_name = Column(String(100), nullable=False)
    database_name = Column(String(100), nullable=False)

    tables = _relationship("ModuleTable", back_populates="module", cascade="all, delete-orphan")
    columns = _relationship("ModuleColumn", back_populates="module", cascade="all, delete-orphan")
    relationships = _relationship("ModuleRelationship", back_populates="module", cascade="all, delete-orphan")

class ModuleTable(Base):
    __tablename__ = "module_tables"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("business_modules.id"), nullable=False)
    table_name = Column(String(100), nullable=False)

    module = _relationship("BusinessModule", back_populates="tables")

class ModuleColumn(Base):
    __tablename__ = "module_columns"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("business_modules.id"), nullable=False)
    table_name = Column(String(100), nullable=False)
    column_name = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)
    is_primary_key = Column(Integer, default=0)

    module = _relationship("BusinessModule", back_populates="columns")

class ModuleRelationship(Base):
    __tablename__ = "module_relationships"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("business_modules.id"), nullable=False)
    relationship = Column(String(500), nullable=False)

    module = _relationship("BusinessModule", back_populates="relationships")
