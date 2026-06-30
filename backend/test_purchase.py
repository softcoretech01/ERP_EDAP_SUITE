import requests
import json

def test_purchase():
    print("--- STARTING PURCHASE AGENT TEST (VIA API) ---")
    url = "http://127.0.0.1:8000/api/chat/ask"
    
    payload = {
        "tenant_id": 1,
        "query": "Show me the total quantity and amount for all Purchase Orders grouped by Vendor.",
        "mode": "db",
        "db_conn_id": 1
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Sending Query: {payload['query']}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        print("\n--- AI RESPONSE ---")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_purchase()
