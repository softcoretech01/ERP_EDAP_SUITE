import urllib.request, urllib.parse, json

try:
    # 1. Login to get token
    data = urllib.parse.urlencode({'username': 'admin', 'password': 'password'}).encode()
    req1 = urllib.request.Request('http://127.0.0.1:8000/api/auth/login', data=data)
    response = urllib.request.urlopen(req1)
    token = json.loads(response.read())['access_token']

    # 2. Ask question
    payload = json.dumps({
        'query': 'how many invoice are creted this year',
        'db_conn_id': 1,
        'session_id': 'test-session-123'
    }).encode()
    req2 = urllib.request.Request(
        'http://127.0.0.1:8000/api/chat/ask',
        data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    
    print("--------------------")
    print(urllib.request.urlopen(req2).read().decode())
    print("--------------------")
except Exception as e:
    print(f"Error: {e}")
