import httpx
import asyncio

async def test_chat():
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "query": "list the items",
            "session_id": "test",
            "db_conn_id": 1
        }
        resp = await client.post("http://127.0.0.1:8000/api/chat/test-ask", json=payload)
        print("Status:", resp.status_code)
        print("Response:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_chat())
