import httpx
import asyncio

async def test_schema_api():
    async with httpx.AsyncClient() as client:
        # Fetch first connection ID
        conn_resp = await client.get("http://127.0.0.1:8000/api/connections")
        conns = conn_resp.json()
        print("Connections:", conns)
        if not isinstance(conns, list) or not conns:
            print("No connections found or invalid format!")
            return
        
        conn_id = conns[0]["id"]
        print(f"Using Connection ID: {conn_id}")

        print("Triggering scan...")
        resp = await client.post(f"http://127.0.0.1:8000/api/schema/scan/{conn_id}?tenant_id=1")
        print(f"Trigger Resp: {resp.status_code} - {resp.text}")
        
        print("Waiting 15 seconds for background scan to process...")
        await asyncio.sleep(15)
        
        print("Fetching pending schemas...")
        resp2 = await client.get("http://127.0.0.1:8000/api/schema/pending?tenant_id=1")
        print(f"Pending Resp: {resp2.status_code}")
        try:
            print(resp2.json())
        except:
            print(resp2.text)

if __name__ == "__main__":
    asyncio.run(test_schema_api())
