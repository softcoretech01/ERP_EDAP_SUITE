from ..ai.ollama_service import ollama_service

class ClassifierService:
    async def classify_query(self, query: str) -> str:
        # Pre-process simple greetings and general questions to ensure they route to CHAT_QUERY
        clean_query = query.strip().lower()
        if clean_query in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]:
            return "CHAT_QUERY"
            
        system_prompt = """
        You are a query classifier for an ERP AI Assistant.
        Classify the user query into exactly one of the following categories:
        
        1. CHAT_QUERY:
           - Conversational greetings (e.g., "hi", "hello", "how are you").
           - Explanations of general concepts or definitions (e.g., "explain ERP", "what is CRM").
           - Questions that do not require executing data queries on the database or searching specific uploaded documents.
           
        2. DASHBOARD:
           - Requests for visual charts, graphs, or comparisons of metrics (e.g., "compare sales this month", "show revenue chart", "sales chart by region", "compare monthly orders").
           
        3. SQL_QUERY:
           - Requests to list, count, retrieve, or query specific records, tables, or facts from the ERP database (e.g., "list customers", "show invoices", "how many orders did we get", "top 10 products sold", "who bought invoice #123", "list all tables").
           
        4. DOCUMENT_QUERY:
           - Queries referring to uploaded files, manuals, PDFs, SOPs, or document summaries (e.g., "summarize uploaded document", "read the attached manual", "what does the uploaded PDF say about pricing").

        Output ONLY the category name: CHAT_QUERY, DASHBOARD, SQL_QUERY, or DOCUMENT_QUERY. No other text.
        """
        
        result = await ollama_service.generate(
            prompt=f"User Query: '{query}'\nCategory:",
            system=system_prompt,
            temperature=0.0,
            num_predict=10
        )
        category = result.strip().upper()
        
        # Clean potential extra chars from LLM
        for valid in ["DASHBOARD", "SQL_QUERY", "DOCUMENT_QUERY", "CHAT_QUERY"]:
            if valid in category:
                return valid
        return "CHAT_QUERY" # Fallback

classifier_service = ClassifierService()

