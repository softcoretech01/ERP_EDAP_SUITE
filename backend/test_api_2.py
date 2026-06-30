import urllib.request, json
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/chat/test-ask",
    data=json.dumps({"query": "Which suppliers are causing delays?", "db_conn_id": 1, "session_id": "test-session-123"}).encode(),
    headers={"Content-Type": "application/json"}
)
print(urllib.request.urlopen(req).read().decode())
lllj