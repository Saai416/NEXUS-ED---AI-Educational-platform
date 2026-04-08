import requests
import time
from database import SessionLocal, PendingVerification, User
from app import pwd_context

BASE_URL = "http://127.0.0.1:8003"

def get_db_otp(identifier):
    db = SessionLocal()
    rec = db.query(PendingVerification).filter(PendingVerification.identifier == identifier).first()
    otp = rec.otp if rec else None
    db.close()
    return otp

def cleanup(email):
    db = SessionLocal()
    db.query(User).filter(User.email == email).delete()
    db.query(PendingVerification).filter(PendingVerification.identifier == email).delete()
    db.commit()
    db.close()

def test_student_flow():
    email = "test_student@example.com"
    username = "test_student"
    cleanup(email)
    
    print("1. Registering Student...")
    res = requests.post(f"{BASE_URL}/api/register", json={
        "username": username,
        "email": email,
        "password": "password123",
        "role": "student"
    })
    
    if res.status_code != 200:
        print("FAILED to register:", res.text)
        return
    
    print("   -> Registered.")
    
    # Get OTP from DB
    otp = get_db_otp(email)
    print(f"   -> OTP found in DB: {otp}")
    
    print("2. Verifying OTP...")
    res = requests.post(f"{BASE_URL}/api/confirm_verification", json={
        "identifier": email,
        "otp": otp
    })
    
    if res.status_code != 200:
        print("FAILED to verify:", res.text)
        return
    print("   -> Verified.")

    print("3. Logging in...")
    res = requests.post(f"{BASE_URL}/login", json={
        "username": username,
        "password": "password123"
    })
    
    if res.status_code == 200:
        print("   -> Login Success! Cookies:", res.cookies.get_dict())
    else:
        print("FAILED to login:", res.text)

def test_teacher_flow():
    email = "test_teacher@example.com"
    username = "test_teacher"
    cleanup(email)
    
    print("\n1. Registering Teacher (Wrong Code)...")
    res = requests.post(f"{BASE_URL}/api/register", json={
        "username": username,
        "email": email,
        "password": "password123",
        "role": "teacher",
        "teacher_code": "WRONG_CODE"
    })
    if res.status_code == 403:
        print("   -> Correctly rejected invalid code.")
    else:
        print("   -> ERROR: Should have been rejected", res.text)

    print("2. Registering Teacher (Correct Code)...")
    res = requests.post(f"{BASE_URL}/api/register", json={
        "username": username,
        "email": email,
        "password": "password123",
        "role": "teacher",
        "teacher_code": "TEACHER_SECRET_2025" # Default in code
    })
    
    if res.status_code != 200:
        print("FAILED to register teacher:", res.text)
        return
        
    print("   -> Teacher Registered.")

if __name__ == "__main__":
    # Ensure app is running outside or start it? 
    # For this environment, we assume the user might not have started it yet.
    # So we'll prompt the user to run it, or try to run it in background.
    # Actually, I can't easily rely on `uvicorn` running in background and being ready instantly.
    # I'll rely on the User to have the server running or I will try to start it.
    print("Starting tests... Ensure uvicorn is running on port 8000.")
    try:
        requests.get(BASE_URL)
        test_student_flow()
        test_teacher_flow()
    except requests.exceptions.ConnectionError:
        print("Server not running. Please start the server with `uvicorn app:app --reload`")
