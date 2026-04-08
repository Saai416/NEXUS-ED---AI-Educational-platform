import requests
import json

BASE_URL = "http://127.0.0.1:8000"
TEXT_TO_UPLOAD = "The advent of powerful AI large language models requires orchestration beyond simple API calls when developing real-world applications. LangChain is an open-source Python framework aiming to simplify every step of the LLM app lifecycle. It provides standard interfaces for chat models, embeddings, vector stores, and integrations across hundreds of providers."
CONTENT_NAME = "LangChain Intro"

def verify_upload():
    session = requests.Session()
    
    print(f"1. Logging in as Teacher...")
    try:
        # Note: Login now uses JSON as per recent fix
        resp = session.post(f"{BASE_URL}/login", json={"username": "teacher", "password": "teacher123"})
        
        if resp.status_code != 200:
            print(f"[FAIL] Login failed: {resp.status_code} - {resp.text}")
            return
            
        print("[OK] Login successful.")
        
        print(f"2. Uploading Content: '{CONTENT_NAME}'...")
        payload = {
            "content_name": CONTENT_NAME,
            "text": TEXT_TO_UPLOAD
        }
        
        resp = session.post(f"{BASE_URL}/api/upload", json=payload)
        
        if resp.status_code == 200:
            data = resp.json()
            print("[OK] Upload Successful!")
            print(f"   Message: {data.get('message')}")
            # print(f"   Graph Data: {json.dumps(data.get('graph_preview'), indent=2)}") 
        else:
            print(f"[FAIL] Upload failed: {resp.status_code}")
            print(f"   Error: {resp.text}")

    except Exception as e:
        print(f"[FAIL] Connection Error: {e}")

if __name__ == "__main__":
    verify_upload()
