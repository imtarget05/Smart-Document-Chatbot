"""
Smart Document Chatbot — System Integration Test
Uses httpx.AsyncClient for non-blocking HTTP calls.
"""

import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8080/api"
USERNAME = "testuser_test"
PASSWORD = "password1234"


async def test_auth(client: httpx.AsyncClient):
    print("--- Testing Auth (Register/Login) ---")
    # Register
    reg_res = await client.post(
        f"{BASE_URL}/auth/register", json={"username": USERNAME, "password": PASSWORD}
    )
    print(f"Register: {reg_res.status_code}")

    # Login
    log_res = await client.post(
        f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD}
    )
    print(f"Login: {log_res.status_code}")
    data = log_res.json()
    return data.get("token")


async def test_upload(client: httpx.AsyncClient, token: str):
    print("--- Testing Upload ---")
    headers = {"Authorization": f"Bearer {token}"}
    files = {
        "file": (
            "test.txt",
            "This is a test document about AI Agents and LangGraph. AI Agents are autonomous systems.",
        )
    }
    res = await client.post(
        f"{BASE_URL}/documents/upload", headers=headers, files=files
    )
    print(f"Upload: {res.status_code}")
    try:
        data = res.json()
        return data.get("documentId")
    except Exception:
        print(f"Upload response parse error: {res.text}")
        return None


async def test_chat(client: httpx.AsyncClient, token: str, doc_id: str):
    print("--- Testing Chat (Standard + History) ---")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    session_id = "test-session-999"

    # 1. Ask question
    payload = {
        "sessionId": session_id,
        "documentId": doc_id,
        "message": "What is this document about?",
        "deepThinking": False,
        "webSearch": False,
    }
    res = await client.post(f"{BASE_URL}/chat/ask", headers=headers, json=payload)
    print(f"Chat Ask: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"AI Response: {data.get('aiResponse', '')[:100]}...")

    # 2. Check sessions list
    sess_res = await client.get(f"{BASE_URL}/chat/sessions", headers=headers)
    print(f"Sessions List: {sess_res.status_code}")
    try:
        sessions = sess_res.json()
        print(f"Sessions found: {len(sessions)}")
    except Exception:
        print(f"Sessions parse error: {sess_res.text[:200]}")


async def test_mindmap(client: httpx.AsyncClient, token: str, doc_id: str):
    print("--- Testing MindMap ---")
    headers = {"Authorization": f"Bearer {token}"}
    # Wait for processing
    print("Waiting for ETL...")
    await asyncio.sleep(5)
    res = await client.get(f"{BASE_URL}/documents/{doc_id}/mindmap", headers=headers)
    print(f"MindMap: {res.status_code}")
    if res.status_code == 200:
        print("MindMap data received successfully.")
    else:
        print(f"MindMap error: {res.text[:200]}")


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            token = await test_auth(client)
            if token:
                doc_id = await test_upload(client, token)
                if doc_id:
                    await test_chat(client, token, doc_id)
                    await test_mindmap(client, token, doc_id)
        except httpx.HTTPError as e:
            print(f"HTTP error: {e}")
        except Exception as e:
            print(f"Test failed: {e}")
            return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
