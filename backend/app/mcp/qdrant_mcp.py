import logging
from typing import List, Dict, Any

from ..services.rag_service import rag_service
from ..services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

class QdrantMCP:
    """
    Model Context Protocol (MCP) layer for Qdrant vector database.
    Allows agents to perform semantic search over schema and docs.
    """
    def __init__(self):
        pass

    async def search_schema(self, tenant_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the schema collection for tables or columns related to the query.
        """
        return qdrant_service.search_vectors(
            collection_name="schema_collection",
            tenant_id=tenant_id,
            query=query,
            limit=limit
        )

    async def search_documents(self, tenant_id: int, query: str, limit: int = 3) -> str:
        """
        Searches general ERP documentation using RAG.
        """
        return await rag_service.query(tenant_id=tenant_id, query_text=query, similarity_top_k=limit)

qdrant_mcp = QdrantMCP()
