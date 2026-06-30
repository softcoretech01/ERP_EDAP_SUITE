import logging
from typing import Optional
from ..services.retrieval_service import retrieval_service
from ..services.context_builder import context_builder

logger = logging.getLogger(__name__)

class SchemaRetrievalAgent:
    """
    Agent 2: Schema Retrieval Agent
    Takes the intent and module, retrieves the most relevant schemas via Hybrid Retrieval,
    and formats them into a compact LLM context.
    """
    async def retrieve_schema_context(self, tenant_id: int, module: str, intent_keywords: str) -> str:
        # We can pass both module and intent to retrieval if needed, 
        # but the query string for embedding usually works best with the keywords.
        search_query = f"{module} {intent_keywords}"
        
        # Call hybrid search (limit set to 15 to balance context and speed)
        top_tables = await retrieval_service.hybrid_search(tenant_id=tenant_id, query=search_query, limit=15)
        
        # Format compact context
        context_str = context_builder.build_schema_context(top_tables)
        
        logger.info(f"SchemaRetrievalAgent produced context of length {len(context_str)}")
        return context_str

schema_retrieval_agent = SchemaRetrievalAgent()
