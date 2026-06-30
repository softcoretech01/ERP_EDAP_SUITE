import logging
import json
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..models.schema_models import SchemaTable, SchemaColumn, BusinessDictionary

logger = logging.getLogger(__name__)

class SchemaEnricher:
    async def enrich_schema(self, db: AsyncSession, tenant_id: int, db_name: str) -> List[Dict[str, Any]]:
        """Reads from schema_tables and produces enriched JSON payloads for embedding and Qdrant."""
        
        # 1. Fetch tables with columns
        stmt = (
            select(SchemaTable)
            .where(SchemaTable.database_name == db_name, SchemaTable.tenant_id == tenant_id)
            .options(selectinload(SchemaTable.columns))
        )
        result = await db.execute(stmt)
        tables = result.scalars().all()
        
        # 2. Fetch business dictionary for this tenant/module
        dict_stmt = select(BusinessDictionary)
        dict_result = await db.execute(dict_stmt)
        business_dict = {entry.business_term.lower(): entry for entry in dict_result.scalars().all()}
        
        enriched_payloads = []
        
        for table in tables:
            # Simple heuristic for business name if not populated
            business_name = table.business_name
            if not business_name:
                parts = table.table_name.replace("tbl_", "").split("_")
                business_name = " ".join([p for p in parts if p])
            
            # Lookup dictionary for this table
            term_entry = business_dict.get(business_name.lower())
            table_keywords = term_entry.synonyms if term_entry and term_entry.synonyms else []
            table_desc = term_entry.description if term_entry else f"{business_name} table"
            
            col_list = []
            col_names = []
            for col in table.columns:
                col_names.append(col.column_name)
                col_meaning = col.business_meaning or col.column_name
                col_list.append({
                    "name": col.column_name,
                    "type": col.data_type,
                    "is_pk": col.is_primary_key,
                    "is_fk": col.is_foreign_key,
                    "business_meaning": col_meaning
                })
                
            payload = {
                "tenant_id": table.tenant_id,
                "database_name": table.database_name,
                "module": table.module_name or "Unknown",
                "table_name": table.table_name,
                "table_type": table.table_type or "Unknown",
                "business_name": business_name,
                "description": table_desc,
                "keywords": table_keywords,
                "columns": col_names,
                "column_details": col_list,
                # relationships are dynamically queried via graph, or we can attach direct ones here
                "relationships": [] 
            }
            enriched_payloads.append(payload)
            
        logger.info(f"Enriched {len(enriched_payloads)} tables for database {db_name}.")
        return enriched_payloads

schema_enricher = SchemaEnricher()
