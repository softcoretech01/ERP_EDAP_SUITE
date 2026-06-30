import asyncio
import time
from app.services.llm_service import llm_service

async def test_llm():
    prompt = """You are an expert SQL Generator for MySQL.
Here are the JSON schema summaries of the relevant tables:
{"table": "item_master", "business_domain": "product", "important_columns": ["id", "item_name"]}

User Request: list the items
Context: 

Generate ONLY the raw MySQL SELECT query required to answer the user's request.
DO NOT wrap the SQL in backticks.
DO NOT provide any explanations.
Output ONLY the SQL query.
"""
    print("Testing LLM generation speed...")
    start = time.time()
    resp = await llm_service.generate(prompt=prompt, system="Output ONLY raw SQL.", temperature=0.0)
    print(f"Time taken: {time.time() - start:.3f}s")
    print(f"Response: {resp}")

if __name__ == "__main__":
    asyncio.run(test_llm())
