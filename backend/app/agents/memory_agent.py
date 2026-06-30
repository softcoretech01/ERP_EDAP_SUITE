import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.memory_service import memory_service
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

class MemoryAgent:
    """
    Agent responsible for extracting, formatting, and summarizing
    chat memory for the Multi-Agent orchestrator.
    """
    def __init__(self):
        pass

    async def get_context(self, db: AsyncSession, session_id: str, limit: int = 5) -> str:
        history = await memory_service.get_history(db, session_id, limit)
        if not history:
            return ""
        
        context_lines = []
        for chat in history:
            # Only include the user question and a cleaned assistant response.
            # We strip any raw database data from old answers to prevent stale
            # numbers from leaking into the next query's final response prompt.
            user_q = chat.question.strip()
            # Truncate very long assistant responses to the first 300 chars to avoid noise
            assistant_resp = chat.response.strip()
            if len(assistant_resp) > 300:
                assistant_resp = assistant_resp[:300] + "..."
            context_lines.append(f"User: {user_q}")
            context_lines.append(f"Assistant: {assistant_resp}")
            
        return "\n".join(context_lines)

    async def summarize_history(self, db: AsyncSession, session_id: str, limit: int = 10) -> str:
        context = await self.get_context(db, session_id, limit)
        if not context:
            return "No previous interaction."
            
        prompt = f"Summarize the following conversation history briefly but keep the most important context and entities:\n\n{context}\n\nSummary:"
        summary = await llm_service.generate(prompt=prompt, system="You are a helpful assistant that summarizes conversation histories for another AI.")
        return summary

memory_agent = MemoryAgent()
