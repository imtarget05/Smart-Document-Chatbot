
import requests
import json
import time

BASE_URL = "http://localhost:8080/api"
USERNAME = "testuser_test"
PASSWORD = "password1234"

def test_auth():
    print("--- Testing Auth (Register/Login) ---")
    # Register
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={"username": USERNAME, "password": PASSWORD})
    print(f"Register: {reg_res.status_code}")
    
    # Login
    log_res = requests.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
    print(f"Login: {log_res.status_code}")
    return log_res.json().get("token")

def test_upload(token):
    print("--- Testing Upload ---")
    headers = {"Authorization": f"Bearer {token}"}
    files = {'file': ('test.txt', 'This is a test document about AI Agents and LangGraph. AI Agents are autonomous systems.')}
    res = requests.post(f"{BASE_URL}/documents/upload", headers=headers, files=files)
    print(f"Upload: {res.status_code}")
    doc_id = res.json().get("documentId")
    return doc_id

def test_chat(token, doc_id):
    print("--- Testing Chat (Standard + History) ---")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    session_id = "test-session-999"
    
    # 1. Ask question
    payload = {
        "sessionId": session_id,
        "documentId": doc_id,
        "message": "What is this document about?",
        "deepThinking": False,
        "webSearch": False
    }
    res = requests.post(f"{BASE_URL}/chat/ask", headers=headers, json=payload)
    print(f"Chat Ask: {res.status_code}")
    if res.status_code == 200:
        print(f"AI Response: {res.json().get('aiResponse')[:100]}...")
    
    # 2. Check sessions list
    sess_res = requests.get(f"{BASE_URL}/chat/sessions", headers=headers)
    print(f"Sessions List: {sess_res.status_code}")
    print(f"Sessions found: {len(sess_res.json())}")

def test_mindmap(token, doc_id):
    print("--- Testing MindMap ---")
    headers = {"Authorization": f"Bearer {token}"}
    # Wait for processing
    print("Waiting for ETL...")
    time.sleep(5)
    res = requests.get(f"{BASE_URL}/documents/{doc_id}/mindmap", headers=headers)
    print(f"MindMap: {res.status_code}")
    if res.status_code == 200:
        print("MindMap data received successfully.")

if __name__ == "__main__":
    try:
        t = test_auth()
        if t:
            d_id = test_upload(t)
            if d_id:
                test_chat(t, d_id)
                test_mindmap(t, d_id)
    except Exception as e:
        print(f"Test failed: {e}")
