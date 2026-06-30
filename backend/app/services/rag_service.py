import logging
from typing import List, Dict, Any

from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from qdrant_client.models import Filter

from ..core.config import settings
from ..core.tenant_manager import tenant_manager
from .llm_service import llm_service
from .qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.collection_name = "document_collection"
        self._setup_done = False

    async def setup_llama_index(self):
        if self._setup_done:
            return

        # Use our LLM Service to get the target model name
        target_model = await llm_service.select_model(settings.OLLAMA_MODEL)
        
        # Set up LLM
        llm = Ollama(model=target_model, base_url=settings.OLLAMA_URL, request_timeout=180.0)
        
        # Set up Embedding Model
        embed_model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL)
        
        # Configure global LlamaIndex Settings
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 512
        Settings.chunk_overlap = 50
        
        self._setup_done = True

    async def get_index(self) -> VectorStoreIndex:
        await self.setup_llama_index()
        
        qdrant_service.init_collections()
        
        vector_store = QdrantVectorStore(
            client=qdrant_service.client, 
            collection_name=self.collection_name
        )
        
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        return index

    async def query(self, tenant_id: int, query_text: str, similarity_top_k: int = 3) -> str:
        index = await self.get_index()
        
        # Create Qdrant filter for tenant isolation
        tenant_filter: Filter = tenant_manager.get_tenant_filter(tenant_id)
        
        # In llama-index-vector-stores-qdrant, we can pass qdrant_filters in vector_store_kwargs
        query_engine = index.as_query_engine(
            similarity_top_k=similarity_top_k,
            vector_store_kwargs={"qdrant_filters": tenant_filter}
        )
        
        # Run synchronous query since we don't have an async qdrant client configured
        response = query_engine.query(query_text)
        return str(response)

    async def get_raw_context(self, tenant_id: int, query_text: str, top_k: int = 15) -> str:
        index = await self.get_index()
        tenant_filter: Filter = tenant_manager.get_tenant_filter(tenant_id)
        
        retriever = index.as_retriever(
            similarity_top_k=top_k,
            vector_store_kwargs={"qdrant_filters": tenant_filter}
        )
        nodes = retriever.retrieve(query_text)
        return "\n\n".join([n.node.get_content() for n in nodes])

    async def index_documents(self, tenant_id: int, texts: List[str], metadata_list: List[Dict[str, Any]] = None):
        index = await self.get_index()
        
        documents = []
        for i, text in enumerate(texts):
            meta = {"tenant_id": tenant_id}
            if metadata_list and i < len(metadata_list):
                meta.update(metadata_list[i])
            documents.append(Document(text=text, metadata=meta))
            
        for doc in documents:
            index.insert(doc)

rag_service = RAGService()
