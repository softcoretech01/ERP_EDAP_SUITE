import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from ..db.database import get_db, test_db_connection
from ..db.connection_manager import connection_manager
from ..auth.permissions import RequiresPermission, get_current_user_token
from ..services.memory_service import memory_service
from ..models.chat_history import ChatHistory
import uuid
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

from typing import Optional

class ChatRequest(BaseModel):
    query: str
    db_conn_id: int
    session_id: Optional[str] = None
    mode: Optional[str] = "db"

class EditRequest(BaseModel):
    edited_message_time: str
    old_content: Optional[str] = None

@router.get("/connections")
async def list_connections(user_id: int = Depends(RequiresPermission("chat_access"))):
    from ..core.config import settings
    target_db = settings.DB_NAME_USER or settings.database_name
    return [{"id": 1, "name": target_db}]

@router.get("/sessions")
async def get_sessions(user_id: int = Depends(RequiresPermission("chat_access")), db: AsyncSession = Depends(get_db)):
    # Group by session_id, showing the latest user message as the title (max 30 chars), sorted by latest updated_at descending
    stmt = select(ChatHistory).where(ChatHistory.user_id == user_id).order_by(ChatHistory.created_at.desc())
    result = await db.execute(stmt)
    histories = result.scalars().all()
    
    grouped = {}
    for h in histories:
        sess_id = h.session_id
        if sess_id not in grouped:
            title = h.question[:30] if h.question else "New Chat"
            grouped[sess_id] = {
                "session_id": sess_id,
                "title": title,
                "updated_at": h.created_at.strftime("%Y-%m-%d") if h.created_at else ""
            }
            
    return list(grouped.values())

@router.get("/sessions/{session_id}")
async def get_session_messages(session_id: str, user_id: int = Depends(RequiresPermission("chat_access")), db: AsyncSession = Depends(get_db)):
    stmt = select(ChatHistory).where(ChatHistory.session_id == session_id, ChatHistory.user_id == user_id).order_by(ChatHistory.created_at.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    formatted = []
    for msg in messages:
        is_dashboard = msg.response.startswith("SQL:") or "Dashboard generated" in msg.response or "Result Table" in msg.response or "Query Result Table" in msg.response
        
        formatted.append({
            "id": f"u-{msg.id}",
            "session_id": session_id,
            "sender": "user",
            "content": msg.question,
            "type": "chat",
            "created_at": msg.created_at.isoformat() if msg.created_at else ""
        })
        
        formatted.append({
            "id": f"a-{msg.id}",
            "session_id": session_id,
            "sender": "assistant",
            "content": msg.response,
            "type": "dashboard" if is_dashboard else "chat",
            "created_at": msg.created_at.isoformat() if msg.created_at else ""
        })
    return formatted

@router.delete("/sessions/{session_id}/edit")
async def delete_from_edited_time(session_id: str, request: EditRequest, user_id: int = Depends(RequiresPermission("chat_access")), db: AsyncSession = Depends(get_db)):
    try:
        from dateutil import parser
        dt = parser.parse(request.edited_message_time)
        # MySQL DateTime without timezone requires naive datetime for comparison
        dt_naive = dt.replace(tzinfo=None)
        await memory_service.delete_from_time(db, session_id, dt_naive, request.old_content)
        return {"success": True, "message": "History updated successfully"}
    except Exception as e:
        logger.error(f"Error updating history on edit: {e}")
        return {"success": False, "message": f"Failed to update history: {str(e)}"}

@router.post("/ask")
async def ask_question(
    request: ChatRequest, 
    user_id: int = Depends(RequiresPermission("chat_access")), 
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    from ..core.tenant_manager import tenant_manager
    from ..agents.agent_orchestrator import agent_orchestrator
    
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        response = await agent_orchestrator.process_request(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            query=request.query,
            mode=request.mode
        )
        return {
            "success": True,
            "message": response,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        return {
            "success": False,
            "type": "error",
            "message": str(e)
        }

@router.post("/test-ask")
async def test_ask_question(
    request: ChatRequest, 
    db: AsyncSession = Depends(get_db)
):
    from ..core.tenant_manager import tenant_manager
    from ..agents.agent_orchestrator import agent_orchestrator
    
    tenant_id = 1
    session_id = request.session_id or str(uuid.uuid4())
    user_id = 1
    
    import time
    start = time.time()
    try:
        response = await agent_orchestrator.process_request(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            query=request.query,
            mode=request.mode
        )
        elapsed = time.time() - start
        return {
            "success": True,
            "message": response,
            "session_id": session_id,
            "time_taken": elapsed
        }
    except Exception as e:
        logger.error(f"Error in test_ask_question: {e}")
        return {
            "success": False,
            "type": "error",
            "message": str(e)
        }


