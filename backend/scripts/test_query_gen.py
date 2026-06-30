import asyncio
import logging
from app.agents.sql_agent import sql_agent
from app.agents.schema_retrieval_agent import schema_retrieval_agent

logging.basicConfig(level=logging.INFO)

async def test():
    query = "Which PRs have not yet become Purchase Orders"
    schema_context_str = await schema_retrieval_agent.retrieve_schema_context(1, "purchase", "PR, Purchase Order")
    
    print("----- SCHEMA CONTEXT -----")
    print(schema_context_str)
    
    error_feedback = ""
    for attempt in range(3):
        print(f"\n--- ATTEMPT {attempt + 1} ---")
        sql = await sql_agent.generate_sql(query, schema_context_str, "", error_feedback)
        print("SQL:", sql)
        
        try:
            # Replace with hardcoded decrypted pw if we knew it, or bypass
            pass
        except Exception as e:
            pass

if __name__ == "__main__":
    asyncio.run(test())
