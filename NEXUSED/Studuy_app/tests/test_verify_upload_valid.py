import requests
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "teacher"
PASSWORD = "Vini@0310"
PDF_PATH = "verify_upload_test.pdf" # Use the valid PDF

def main():
    print(f"--- Verify Valid PDF Upload: {PDF_PATH} ---")
    
    session = requests.Session()
    # Login
    try:
        resp = session.post(f"{BASE_URL}/login", json={"username": USERNAME, "password": PASSWORD})
        if not resp.ok and resp.status_code != 303:
             print("Login failed, cannot proceed.")
             return
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    # Upload
    if not os.path.exists(PDF_PATH):
        print(f"File {PDF_PATH} missing!")
        return

    with open(PDF_PATH, 'rb') as f:
        files = {'file': (PDF_PATH, f, 'application/pdf')}
        data = {'content_name': 'Valid PDF Verification', 'source': 'file'}
        resp = session.post(f"{BASE_URL}/api/upload", files=files, data=data)
        
        print(f"Upload Status: {resp.status_code}")
        print(f"Response Body: {resp.text}")

if __name__ == "__main__":
    main()
