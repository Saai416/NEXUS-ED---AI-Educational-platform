import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_login_page():
    print(f"Testing GET {BASE_URL}/...")
    try:
        resp = requests.get(BASE_URL)
        if resp.status_code == 200 and "Login" in resp.text:
            print("[OK] Login Page Loaded")
        else:
            print(f"[FAIL] Login Page Failed: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] Connection Failed: {e}")

def test_teacher_flow():
    print("\nTesting Teacher Flow...")
    session = requests.Session()
    
    # Login
    login_data = {"username": "teacher", "password": "teacher123"}
    resp = session.post(f"{BASE_URL}/login", data=login_data)
    
    # Check redirect or cookie
    if resp.status_code == 200 and session.cookies.get("role") == "teacher":
         print("[OK] Login Successful")
    else:
         print(f"[FAIL] Login Failed: {resp.status_code} -Cookies: {session.cookies.get_dict()}")
         return

    # Check Dashboard
    resp = session.get(f"{BASE_URL}/teacher")
    if resp.status_code == 200 and "Teacher Dashboard" in resp.text:
        print("[OK] Teacher Dashboard Accessible")
    else:
        print(f"[FAIL] Teacher Dashboard Failed: {resp.status_code}")

    # Upload Content (Using < 5 lines)
    text = "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to create oxygen and energy in the form of sugar."
    payload = {
        "content_name": "Photosynthesis Intro",
        "text": text
    }
    
    # Note: Using json=payload for requests to send valid JSON body
    resp = session.post(f"{BASE_URL}/api/upload", json=payload)
    if resp.status_code == 200:
        print("[OK] Content Upload Successful")
        print(f"   Response: {resp.json().get('message')}")
    else:
        print(f"[FAIL] Content Upload Failed: {resp.status_code} - {resp.text}")

def test_student_flow():
    print("\nTesting Student Flow...")
    session = requests.Session()
    
    # Login
    login_data = {"username": "student", "password": "student123"}
    resp = session.post(f"{BASE_URL}/login", data=login_data)
    
    if resp.status_code == 200 and session.cookies.get("role") == "student":
         print("[OK] Login Successful")
    else:
         print(f"[FAIL] Login Failed: {resp.status_code}")
         return

    # Check Dashboard
    resp = session.get(f"{BASE_URL}/student")
    if resp.status_code == 200 and "Student Dashboard" in resp.text:
        print("[OK] Student Dashboard Accessible")
    else:
        print(f"[FAIL] Student Dashboard Failed: {resp.status_code}")

    # Chat
    payload = {
        "question": "What is photosynthesis?",
        "namespace": "Photosynthesis Intro"
    }
    resp = session.post(f"{BASE_URL}/api/chat", json=payload)
    if resp.status_code == 200:
        print("[OK] Chat API Successful")
        print(f"   Answer: {str(resp.json().get('answer'))[:50]}...")
    else:
        print(f"[FAIL] Chat API Failed: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    test_login_page()
    test_teacher_flow()
    test_student_flow()
