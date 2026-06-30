import logging
import uuid
import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from ..core.config import settings
from .embeddings_service import embeddings_service
import portalocker

logger = logging.getLogger(__name__)

_qdrant_client = None

def init_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        try:
            if settings.QDRANT_MODE.lower() == "local":
                qdrant_path = os.path.join(os.getcwd(), "qdrant_data_v2")
                os.makedirs(qdrant_path, exist_ok=True)
                _qdrant_client = QdrantClient(path=qdrant_path)
            else:
                _qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            print("Initializing Qdrant client...")
            logger.info("Initializing Qdrant client...")
        except portalocker.exceptions.AlreadyLocked as e:
            logger.error("Qdrant storage is locked by another process.")
            raise RuntimeError("Qdrant storage is locked by another process") from e

def get_qdrant_client():
    if _qdrant_client is None:
        init_qdrant()
    return _qdrant_client

class QdrantService:
    def __init__(self):
        self.collections = ["schema_collection", "business_metadata", "query_history", "document_collection"]
        self._initialized = False

    @property
    def client(self):
        return get_qdrant_client()

    def init_collections(self):
        if self._initialized:
            return
        
        # Get embedding dimension dynamically
        vector_dim = embeddings_service.get_dimension()
        
        try:
            existing = self.client.get_collections()
            existing_names = {c.name for c in existing.collections}
            
            for col in self.collections:
                if col not in existing_names:
                    logger.info(f"QdrantService: Creating collection '{col}' with dimension {vector_dim} (Distance: COSINE)...")
                    self.client.create_collection(
                        collection_name=col,
                        vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                    )
                else:
                    # Validate existing collection dimension
                    col_info = self.client.get_collection(col)
                    existing_dim = None
                    try:
                        vectors_config = col_info.config.params.vectors
                        if hasattr(vectors_config, 'size'):
                            existing_dim = vectors_config.size
                        elif isinstance(vectors_config, dict):
                            existing_dim = vectors_config.get('size')
                    except Exception:
                        pass
                        
                    if existing_dim and existing_dim != vector_dim:
                        logger.warning(f"Qdrant Dimension Mismatch in '{col}': expected {vector_dim}, but found {existing_dim}. Recreating collection...")
                        self.client.delete_collection(col)
                        self.client.create_collection(
                            collection_name=col,
                            vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                        )
            self._initialized = True
        except Exception as e:
            logger.error(f"QdrantService: Initialization of collections failed: {e}")
            raise e

    def upsert_vector(self, collection_name: str, tenant_id: int, text: str, metadata: Dict[str, Any], point_id: str = None) -> str:
        self.init_collections()
        
        p_id = point_id or str(uuid.uuid4())
        vector = embeddings_service.embed_text(text)

        # ==== QDRANT UPSERT START ====
        logger.info("===== QDRANT UPSERT START =====")
        logger.info(f"collection: {collection_name}, tenant_id: {tenant_id}, payload_keys: {list(metadata.keys())}")
        logger.info(f"vector_dim: {len(vector)}")

        # Build payload adding tenant isolation attributes
        payload = {
            "text": text,
            "tenant_id": tenant_id,
            **metadata
        }

        point = PointStruct(
            id=p_id,
            vector=vector,
            payload=payload
        )

        self.client.upsert(
            collection_name=collection_name,
            points=[point]
        )
        # ==== POST UPSERT LOGGING ====
        cnt = self.client.count(collection_name=collection_name)
        logger.info(f"collection_count after upsert: {cnt.count}")
        logger.info("===== QDRANT UPSERT SUCCESS =====")
        return p_id

    def search_vectors(self, collection_name: str, tenant_id: int, query: str, limit: int = 5, extra_conditions: List[Any] = None) -> List[Dict[str, Any]]:
        import time
        total_start = time.time()
        self.init_collections()
        
        embed_start = time.time()
        query_vector = embeddings_service.embed_query(query)
        embed_elapsed = time.time() - embed_start
        
        # Build strict tenant isolation filter
        must_conditions = [
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value=tenant_id)
            )
        ]
        
        if extra_conditions:
            must_conditions.extend(extra_conditions)
            
        search_filter = Filter(must=must_conditions)
        
        search_start = time.time()
        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=search_filter,
            limit=limit
        )
        search_elapsed = time.time() - search_start
        
        total_elapsed = time.time() - total_start
        logger.info(
            f"PERF | Qdrant '{collection_name}' | "
            f"Embedding: {embed_elapsed:.3f}s | "
            f"Search: {search_elapsed:.3f}s | "
            f"Total: {total_elapsed:.3f}s | "
            f"Results: {len(results.points)}"
        )
        return [hit.payload for hit in results.points]

    def delete_by_tenant(self, collection_name: str, tenant_id: int):
        self.init_collections()
        tenant_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )
            ]
        )
        self.client.delete(
            collection_name=collection_name,
            points_selector=tenant_filter
        )

    def validate_qdrant(self):
        """Validate that the schema collection exists, has the correct dimension and is not empty."""
        try:
            coll = "schema_collection"
            info = self.client.get_collection(coll)
            vec_dim = getattr(info.config.params.vectors, "size", None)
            embed_dim = embeddings_service.get_dimension()
            if vec_dim != embed_dim:
                raise RuntimeError(f"Qdrant dimension mismatch: collection={vec_dim}, embedding={embed_dim}")
            cnt = self.client.count(collection_name=coll)
            logger.info(f"QDRANT VALIDATION – {coll}: count={cnt.count}, dim={vec_dim}")
        except Exception as e:
            logger.error(f"QDRANT validation failed: {e}")
            raise
qdrant_service = QdrantService()
