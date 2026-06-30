import logging
import re
from typing import Any
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)


class ResponseFormatterAgent:
    """
    Agent 5: Response Formatter Agent
    
    Sits between SQL execution and the frontend.
    Takes raw SQL result data + the user query, detects the response type,
    and produces a clean, professional, business-friendly response.

    GUARANTEES:
    - Never exposes "Raw Database Data", SQL, table names, column names
    - Always formats numbers using the Indian number system (Crores/Lakhs)
    - Selects the correct template (KPI / Aggregation / List / Trend / Analytics)
    - Returns user-friendly error messages on failure
    """

    # ------------------------------------------------------------------ #
    #  Intent Classification (fast, regex-based — no LLM call needed)     #
    # ------------------------------------------------------------------ #

    _KPI_PATTERNS = re.compile(
        r'\b(how many|count|number of|total count|how much)\b',
        re.IGNORECASE
    )
    _AGGREGATION_PATTERNS = re.compile(
        r'\b(total value|total amount|sum|aggregate|grand total|purchase value|sales amount|revenue)\b',
        re.IGNORECASE
    )
    _LIST_PATTERNS = re.compile(
        r'\b(show|list|display|find|get|fetch|pending|overdue|open|active|top \d+)\b',
        re.IGNORECASE
    )
    _TREND_PATTERNS = re.compile(
        r'\b(trend|compare|vs|versus|last month|previous month|last year|this month|this year|monthly|yearly|growth|change)\b',
        re.IGNORECASE
    )
    _ANALYTICS_PATTERNS = re.compile(
        r'\b(why|insight|reason|analysis|analyse|analyze|suggest|recommendation|improve)\b',
        re.IGNORECASE
    )

    def _detect_intent(self, query: str) -> str:
        """Return one of: KPI | AGGREGATION | LIST | TREND | ANALYTICS"""
        if self._TREND_PATTERNS.search(query):
            return "TREND"
        if self._ANALYTICS_PATTERNS.search(query):
            return "ANALYTICS"
        if self._AGGREGATION_PATTERNS.search(query):
            return "AGGREGATION"
        if self._KPI_PATTERNS.search(query):
            return "KPI"
        if self._LIST_PATTERNS.search(query):
            return "LIST"
        # Default to LIST for unknown queries (safest generic format)
        return "LIST"

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def format(self, user_query: str, sql_result: str, conversation_context: str = "") -> str:
        """
        Convert raw SQL result into a business-friendly response.

        Args:
            user_query:             The original user question.
            sql_result:             Raw markdown-table string from SQL execution.
            conversation_context:   Prior conversation turns (used for trend queries).

        Returns:
            A clean, formatted business response string.
        """
        # Guard: empty or error result
        if not sql_result or not sql_result.strip():
            return "No matching records were found."

        if sql_result.startswith("Error:"):
            logger.warning(f"ResponseFormatterAgent received error result: {sql_result}")
            return "I couldn't find sufficient data to answer this question. Please try rephrasing your query."

        intent = self._detect_intent(user_query)
        logger.info(f"ResponseFormatterAgent | Intent: {intent} | Query: {user_query[:80]}")

        formatted = await self._call_llm(user_query, sql_result, intent, conversation_context)
        return formatted

    # ------------------------------------------------------------------ #
    #  LLM Formatting                                                      #
    # ------------------------------------------------------------------ #

    async def _call_llm(
        self,
        user_query: str,
        sql_result: str,
        intent: str,
        conversation_context: str
    ) -> str:
        template_instructions = self._get_template_instructions(intent)

        system_prompt = (
            "You are an ERP AI Business Assistant. Convert the provided business data into a "
            "clean, professional response.\n\n"

            "====================================================\n"
            "ABSOLUTE PROHIBITIONS\n"
            "=====================\n"
            "NEVER use or mention ANY of these terms:\n"
            "  - Raw Database Data\n"
            "  - SQL Query / Executed SQL / Database Result\n"
            "  - Schema / Table Name / Column Name\n"
            "  - Module Detection / Query Classification\n"
            "  - 'Based on the provided data'\n"
            "  - 'According to the database'\n"
            "  - 'Based on the query result'\n"
            "NEVER show raw unformatted numbers like 85329101955.3450.\n"
            "NEVER hallucinate or invent numbers not present in the data.\n"
            "NEVER mention trends if comparison data does not exist.\n\n"

            "====================================================\n"
            "NUMBER FORMATTING (MANDATORY)\n"
            "=============================\n"
            "Indian number system:\n"
            "  1 Lakh  = 100,000\n"
            "  1 Crore = 10,000,000\n\n"
            "Rules:\n"
            "  value >= 10,000,000 → 'INR X.XX Crores'  (divide by 10,000,000)\n"
            "  value >= 100,000    → 'INR X.XX Lakhs'   (divide by 100,000)\n"
            "  value <  100,000    → 'INR X,XXX'         (comma-formatted)\n"
            "  Plain counts        → comma-formatted (e.g. 2,959)\n"
            "  Always prefix monetary amounts with INR.\n"
            "  Round to 2 decimal places. NEVER lose accuracy.\n\n"
            "  Examples:\n"
            "    85329101955.3450 → INR 8,532.9 Crores\n"
            "    2959             → 2,959\n"
            "    150000           → INR 1.5 Lakhs\n\n"

            f"====================================================\n"
            f"RESPONSE TEMPLATE TO USE: {intent}\n"
            f"====================================================\n"
            f"{template_instructions}\n\n"

            "====================================================\n"
            "ERROR HANDLING\n"
            "==============\n"
            "If data is empty or missing: 'No matching records were found.'\n"
            "If data is insufficient: 'I couldn't find sufficient data to answer this question.'\n"
        )

        # Build a clean data block — no "Raw Database Data" label
        context_block = f"[Prior Conversation]:\n{conversation_context}\n\n" if conversation_context.strip() else ""

        prompt = (
            f"{context_block}"
            f"[Business Data]:\n{sql_result}\n\n"
            f"User Question: {user_query}\n\n"
            "Format this into a professional business response using the template above."
        )

        try:
            result = await llm_service.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.1,
                num_predict=400
            )
            return result.strip()
        except Exception as e:
            logger.error(f"ResponseFormatterAgent LLM error: {e}")
            return "The requested information could not be retrieved. Please try rephrasing your question."

    # ------------------------------------------------------------------ #
    #  Template Instructions per Intent                                    #
    # ------------------------------------------------------------------ #

    def _get_template_instructions(self, intent: str) -> str:
        templates = {
            "KPI": (
                "Use the KPI format:\n\n"
                "  [Descriptive Business Title]\n\n"
                "  • Total [Entity]: [Formatted Number]\n\n"
                "Example output:\n"
                "  Purchase Request Summary\n\n"
                "  • Total Purchase Requests: 2,959\n\n"
                "Rules:\n"
                "  - Title must be business-friendly (no technical terms)\n"
                "  - Show only the direct answer — no analysis, no trend\n"
                "  - One bullet per metric\n"
            ),
            "AGGREGATION": (
                "Use the Aggregation format:\n\n"
                "  [Descriptive Business Title]\n\n"
                "  • [Metric Label]: [INR Formatted Amount]\n"
                "  [Optional one-line business context]\n\n"
                "Example output:\n"
                "  Purchase Order Summary\n\n"
                "  • Total Active PO Value: INR 8,532.9 Crores\n"
                "  This represents the combined value of all currently active purchase orders.\n\n"
                "Rules:\n"
                "  - Always use INR prefix + Crores/Lakhs for monetary values\n"
                "  - Do NOT add trend or suggestion unless data supports it\n"
                "  - Keep the optional explanation to 1 line\n"
            ),
            "LIST": (
                "Use the List format:\n\n"
                "  [Descriptive Business Title]\n\n"
                "  Found [N] records.\n\n"
                "  [Row 1: Field1 | Field2 | Field3]\n"
                "  [Row 2: Field1 | Field2 | Field3]\n"
                "  ...\n\n"
                "Example output:\n"
                "  Pending Purchase Orders\n\n"
                "  Found 24 orders.\n\n"
                "  PO-1001 | ABC Supplier | INR 12.5 Lakhs | Pending\n"
                "  PO-1002 | XYZ Supplier | INR 8.2 Lakhs  | Pending\n\n"
                "Rules:\n"
                "  - Use business-friendly column labels (not raw column names)\n"
                "  - Format all amounts in INR Crores/Lakhs as appropriate\n"
                "  - Max 20 rows in response; if more exist, note 'Showing top 20 records'\n"
            ),
            "TREND": (
                "IMPORTANT: Only use this format if BOTH current AND previous period data exist in the Business Data.\n"
                "If only one period is available, use the Aggregation format instead.\n\n"
                "Trend format:\n\n"
                "  [Descriptive Business Title]\n\n"
                "  • Current [Period]: [INR Amount]\n"
                "  • Previous [Period]: [INR Amount]\n"
                "  • Change: [+/-X.X%]\n\n"
                "  Insight: [One-line factual insight strictly from the data]\n\n"
                "Example output:\n"
                "  Purchase Order Trend — June vs May 2025\n\n"
                "  • Current Month (June): INR 8,532.9 Crores\n"
                "  • Last Month (May): INR 7,980.4 Crores\n"
                "  • Change: +6.9%\n\n"
                "  Insight: Purchase order value grew by 6.9% month-over-month.\n\n"
                "Rules:\n"
                "  - Calculate Change % accurately from the data\n"
                "  - Insight must be factual — do not guess causes\n"
            ),
            "ANALYTICS": (
                "Use the Analytics format:\n\n"
                "  [Descriptive Business Title]\n\n"
                "  Metrics:\n"
                "  • [Metric 1]: [Value]\n"
                "  • [Metric 2]: [Value]\n\n"
                "  Insight:\n"
                "  [2-3 sentence factual insight from the data only]\n\n"
                "  Recommendation:\n"
                "  [1-2 actionable suggestions — only if data supports them]\n\n"
                "Rules:\n"
                "  - Only write insights that are directly supported by the data\n"
                "  - Do NOT invent causes, trends, or reasons\n"
                "  - Do NOT add recommendations if data is insufficient\n"
            ),
        }
        return templates.get(intent, templates["LIST"])


response_formatter_agent = ResponseFormatterAgent()
