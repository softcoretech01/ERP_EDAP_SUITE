import logging
from sentence_transformers import SentenceTransformer
from ..core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingsService:
    def __init__(self):
        # Configurable model, default to BAAI/bge-base-en-v1.5 for production RAG
        self.model_name = getattr(settings, "EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
        try:
            logger.info(f"EmbeddingsService: Initializing with model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("EmbeddingsService: Model loaded successfully.")
        except Exception as e:
            logger.warning(f"EmbeddingsService: Failed to load preferred model {self.model_name} ({e}). Falling back to 'BAAI/bge-base-en-v1.5'.")
            self.model_name = "BAAI/bge-base-en-v1.5"
            self.model = SentenceTransformer(self.model_name)
            logger.info("EmbeddingsService: Fallback model loaded successfully.")

    def get_dimension(self) -> int:
        return int(self.model.get_embedding_dimension())

    def get_model_name(self) -> str:
        return self.model_name

    def embed_text(self, text: str) -> list[float]:
        import time
        start = time.time()
        res = self.model.encode(text).tolist()
        elapsed = time.time() - start
        logger.info(f"Performance: Embedding generated in {elapsed:.3f}s")
        return res

    def embed_query(self, query: str) -> list[float]:
        # BGE models use a specific prefix for query embedding to improve retrieval accuracy
        if "bge" in self.model_name.lower():
            bge_query = f"Represent this sentence for searching relevant passages: {query}"
            return self.embed_text(bge_query)
        return self.embed_text(query)

embeddings_service = EmbeddingsService()
