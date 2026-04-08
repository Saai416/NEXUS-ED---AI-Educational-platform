import requests

try:
    resp = requests.post("http://127.0.0.1:8000/login", json={"username": "student", "password": "student123"})
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
