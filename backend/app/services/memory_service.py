from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from ..models.chat_history import ChatHistory
from datetime import datetime

class MemoryService:
    async def save_interaction(self, db: AsyncSession, session_id: str, user_id: int, question: str, response: str, parent_id: int = None) -> ChatHistory:
        chat = ChatHistory(session_id=session_id, user_id=user_id, question=question, response=response, parent_id=parent_id)
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat

    async def get_history(self, db: AsyncSession, session_id: str, limit: int = 5) -> list[ChatHistory]:
        stmt = select(ChatHistory).where(ChatHistory.session_id == session_id).order_by(ChatHistory.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        history = list(result.scalars().all())
        history.reverse()
        return history

    async def edit_message(self, db: AsyncSession, message_id: int, new_question: str) -> ChatHistory:
        stmt = select(ChatHistory).where(ChatHistory.id == message_id)
        result = await db.execute(stmt)
        message = result.scalars().first()
        
        if message:
            del_stmt = delete(ChatHistory).where(ChatHistory.session_id == message.session_id, ChatHistory.created_at > message.created_at)
            await db.execute(del_stmt)
            message.question = new_question
            await db.commit()
            
        return message

    async def delete_from_time(self, db: AsyncSession, session_id: str, edited_message_time: datetime, old_content: str = None):
        if old_content:
            # Look up the message by exact content to avoid timezone string mismatches
            stmt = select(ChatHistory).where(ChatHistory.session_id == session_id, ChatHistory.question == old_content).order_by(ChatHistory.id.desc()).limit(1)
            result = await db.execute(stmt)
            msg = result.scalars().first()
            if msg:
                del_stmt = delete(ChatHistory).where(ChatHistory.session_id == session_id, ChatHistory.id >= msg.id)
                await db.execute(del_stmt)
                await db.commit()
                return

        # Fallback to time-based deletion
        stmt = delete(ChatHistory).where(
            ChatHistory.session_id == session_id,
            ChatHistory.created_at >= edited_message_time
        )
        await db.execute(stmt)
        await db.commit()

memory_service = MemoryService()

