import logging
from typing import Dict, Any, Tuple
import json
import re
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

class RouterAgent:
    """
    Agent 1: Router + Intent Agent
    Analyzes the user's query to detect the target ERP module and the exact business intent.
    Returns: (module_name, intent_keywords)
    """
    def __init__(self):
        # Basic rule-based routing for speed
        self.rules = {
            "document": ['manual', 'policy', 'documentation', 'guide'],
            "general": ['define', 'what is', 'explain', 'how to', 'meaning', 'hi', 'hello', 'hey', 'how are you', 'who are you', 'help', 'morning', 'afternoon', 'evening', 'good', 'thanks', 'thank you'],
            "purchase": ['purchase', 'vendor', 'supplier', 'procure', 'procurement', 'po', 'pr'],
            "sales": ['customer', 'client', 'sales', 'invoice', 'salesorder', 'quotation'],
            "inventory": ['item', 'product', 'stock', 'warehouse', 'inventory', 'bin'],
            "finance": ['payment', 'balance', 'accounts', 'profit', 'loss', 'tax', 'gst'],
            "hr": ['employee', 'staff', 'hr', 'payroll', 'salary', 'attendance']
        }

    async def route_intent(self, query: str) -> Tuple[str, str]:
        query_lower = query.lower()
        module = "unknown"
        
        for mod, keywords in self.rules.items():
            if any(re.search(rf'\b{kw}s?\b', query_lower) for kw in keywords):
                # Prevent misrouting data queries (e.g. "what is my spend") to general definitions
                if mod == "general":
                    data_keywords = ['my', 'total', 'count', 'sum', 'value', 'spend', 'list', 'show', 'report', 'amount', 'average', 'current', 'how many']
                    if any(re.search(rf'\b{dk}\b', query_lower) for dk in data_keywords):
                        continue
                module = mod
                break
                
        # 2. Extract specific intent
        # OPTIMIZATION: Skipping the LLM call here saves 2-5 seconds.
        # Hybrid Search handles stop words and synonyms naturally, so we can just use the raw query.
        if module == "general":
            return "general", "general"
        
        intent_keywords = query

            
        logger.info(f"RouterAgent detected Module: '{module}', Intent: '{intent_keywords}'")
        return module, intent_keywords

router_agent = RouterAgent()
