from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..db.database import Base

class SchemaTable(Base):
    __tablename__ = "schema_tables"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    database_name = Column(String(100), index=True, nullable=False)
    table_name = Column(String(100), index=True, nullable=False)
    module_name = Column(String(50), index=True, nullable=True)
    table_type = Column(String(50), nullable=True)  # Header, Detail, Master, etc.
    business_name = Column(String(200), nullable=True)

    columns = relationship("SchemaColumn", back_populates="table", cascade="all, delete-orphan")


class SchemaColumn(Base):
    __tablename__ = "schema_columns"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String(100), index=True, nullable=False)
    data_type = Column(String(50), nullable=False)
    is_primary_key = Column(Boolean, default=False)
    is_foreign_key = Column(Boolean, default=False)
    business_meaning = Column(String(255), nullable=True)

    table = relationship("SchemaTable", back_populates="columns")


class SchemaRelationship(Base):
    __tablename__ = "schema_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_table = Column(String(100), index=True, nullable=False)
    source_column = Column(String(100), nullable=False)
    target_table = Column(String(100), index=True, nullable=False)
    target_column = Column(String(100), nullable=False)


class KeywordMapping(Base):
    __tablename__ = "keyword_mappings"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(100), index=True, nullable=False)
    mapped_entity = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)  # table, column


class BusinessDictionary(Base):
    __tablename__ = "business_dictionary"

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(50), index=True, nullable=False)
    business_term = Column(String(100), index=True, nullable=False)
    synonyms = Column(JSON, nullable=True)  # List of synonyms
    description = Column(Text, nullable=True)
