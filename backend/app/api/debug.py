from fastapi import APIRouter
from ..services.qdrant_service import qdrant_service

router = APIRouter(tags=["debug"])

@router.get("/qdrant")
async def qdrant_debug():
    """Return summary of Qdrant collections, counts and vector dimensions."""
    try:
        collections = qdrant_service.client.get_collections()
        result = {"collections": [], "details": {}}
        for col in collections.collections:
            name = col.name
            cnt = qdrant_service.client.count(collection_name=name)
            info = qdrant_service.client.get_collection(name)
            result["collections"].append(name)
            result["details"][name] = {
                "count": cnt.count,
                "vector_size": getattr(info.config.params.vectors, "size", None),
            }
        return result
    except Exception as e:
        return {"error": str(e)}

@router.post("/reset-qdrant")
async def reset_qdrant():
    """Clear all Qdrant collections to wipe fake schemas."""
    try:
        collections = qdrant_service.client.get_collections()
        for col in collections.collections:
            qdrant_service.client.delete_collection(col.name)
        qdrant_service._initialized = False
        qdrant_service.init_collections()
        return {"message": "All Qdrant collections have been wiped clean."}
    except Exception as e:
        return {"error": str(e)}

@router.get("/search")
async def debug_search(query: str):
    try:
        results = qdrant_service.search_vectors("schema_collection", 1, query, limit=5)
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}

@router.post("/test-pipeline")
async def debug_test_pipeline(query: str):
    from ..db.database import AsyncSessionLocal
    from ..agents.agent_orchestrator import agent_orchestrator
    try:
        async with AsyncSessionLocal() as db:
            response = await agent_orchestrator.process_request(
                db=db, 
                user_id=1, 
                tenant_id=1, 
                session_id="test-session-debug", 
                query=query
            )
            return {"query": query, "response": response}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@router.post("/trigger-ingestion")
async def debug_trigger_ingestion():
    from ..core.queue_manager import queue_manager
    try:
        # Assuming tenant 1, connection 1
        await queue_manager.enqueue_scan(1, 1)
        return {"message": "Ingestion scan queued for connection 1"}
    except Exception as e:
        return {"error": str(e)}
