from sqlalchemy.ext.asyncio import AsyncSession
from .classifier_service import classifier_service
from .schema_service import schema_service
from .sql_service import sql_service
from .dashboard_service import dashboard_service
from .rag_service import rag_service
from .memory_service import memory_service
from ..ai.ollama_service import ollama_service

class ChatService:
    async def process_query(self, db: AsyncSession, query: str, user_id: int, session_id: str, db_conn_id: int, host: str, port: int, user: str, encrypted_password: str, db_name: str) -> dict:
        category = await classifier_service.classify_query(query)
        
        response_data = None
        text_response = ""

        if category == "DASHBOARD":
            schema = await schema_service.extract_schema(db_conn_id, host, port, user, encrypted_password, db_name)
            response_data = await dashboard_service.generate_dashboard(query, schema, db_conn_id, host, port, user, encrypted_password, db_name)
            text_response = response_data.get("summary", "Dashboard generated.")
            
            await memory_service.save_interaction(db, session_id, user_id, query, text_response)
            
            return {
                "success": True,
                "type": "dashboard",
                "session_id": session_id,
                "result": response_data
            }
            
        elif category == "SQL_QUERY":
            schema = await schema_service.extract_schema(db_conn_id, host, port, user, encrypted_password, db_name)
            sql = await sql_service.generate_sql(query, schema)
            data = await sql_service.execute_query(sql, db_conn_id, host, port, user, encrypted_password, db_name, schema)
            
            # Format table data as a standardized dashboard response
            chart_type = "table"
            labels = []
            datasets = []
            if data:
                keys = list(data[0].keys())
                labels = [str(row[keys[0]]) for row in data]
                for key in keys[1:]:
                    datasets.append({
                        "label": key,
                        "data": [row[key] for row in data]
                    })
                if not datasets and len(keys) == 1:
                    datasets.append({
                        "label": keys[0],
                        "data": [row[keys[0]] for row in data]
                    })
            
            response_data = {
                "title": "Query Result Table",
                "chartType": chart_type,
                "summary": f"SQL: {sql}\nFound {len(data)} rows.",
                "data": {
                    "labels": labels,
                    "datasets": datasets
                }
            }
            text_response = response_data["summary"]
            
            await memory_service.save_interaction(db, session_id, user_id, query, text_response)
            
            return {
                "success": True,
                "type": "dashboard",
                "session_id": session_id,
                "result": response_data
            }
            
        elif category == "DOCUMENT_QUERY":
            docs = await rag_service.query_documents(query)
            context = "\n".join([doc.get("text", "") for doc in docs])
            
            prompt = f"Answer the user query based ONLY on the following context:\n{context}\n\nQuery: {query}"
            text_response = await ollama_service.generate(prompt)
            
            await memory_service.save_interaction(db, session_id, user_id, query, text_response)
            
            return {
                "success": True,
                "type": "chat",
                "session_id": session_id,
                "message": text_response
            }
            
        else: # CHAT_QUERY
            history = await memory_service.get_history(db, session_id, limit=3)
            history_text = "\n".join([f"User: {h.question}\nAssistant: {h.response}" for h in history])
            system_prompt = (
                "You are a helpful, friendly ERP AI Assistant. Answer general conversational greetings "
                "(like hi, hello, how are you) and general questions in a polite, helpful, and concise manner."
            )
            prompt = f"{history_text}\nUser: {query}\nAssistant:"
            text_response = await ollama_service.generate(prompt, system=system_prompt)
            
            await memory_service.save_interaction(db, session_id, user_id, query, text_response)
            
            return {
                "success": True,
                "type": "chat",
                "session_id": session_id,
                "message": text_response
            }

chat_service = ChatService()

