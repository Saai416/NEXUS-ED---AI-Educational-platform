import requests
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "teacher"
PASSWORD = "Vini@0310"
TEACHER_CODE = "TEACHER_SECRET_2025"
PDF_PATH = "test2.pdf"

def main():
    print(f"--- Starting Test with User: {USERNAME} ---")
    
    # 1. Try Login
    session = requests.Session()
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    print("Attempting login...")
    try:
        resp = session.post(f"{BASE_URL}/login", json=login_data, allow_redirects=False)
        
        if resp.status_code == 303:
            print("Login Successful!")
            # Update session cookies from response
            session.cookies.update(resp.cookies)
        else:
            print(f"Login Failed via POST (Status {resp.status_code}). Response: {resp.text}")
            # Try Signup if login failed
            print("Attempting Signup...")
            signup_data = {
                "username": USERNAME,
                "email": "teacher@test.com",
                "password": PASSWORD,
                "role": "teacher",
                "teacher_code": TEACHER_CODE
            }
            resp_signup = session.post(f"{BASE_URL}/api/signup", json=signup_data)
            print(f"Signup Response: {resp_signup.status_code} - {resp_signup.text}")
            
            if resp_signup.ok:
                print("Signup successful based on API. Note: Verification might be required.")
                # Retrieve OTP from console would be needed, but for now let's hope manual verification isn't strictly enforced for this test or we can check DB.
                # Actually, the app requires verification.
                # Let's check if we can verify directly or if the user is already verified.
                
                # For this test, we assume the user might already exist or we just need to hit login again after manual verification.
                # Since we can't easily get the mockup OTP programmatically without reading stdout of the OTHER process, 
                # we might be blocked if signup is fresh. 
                # HOWEVER, user provided credentials, so likely account exists.
                pass
            else:
                 print("Signup failed or user already exists.")

            # Retry login
            resp = session.post(f"{BASE_URL}/login", json=login_data, allow_redirects=False)
            if resp.status_code == 303:
                print("Login Successful after signup attempt!")
                session.cookies.update(resp.cookies)
            else:
                print("Login still failed. Aborting upload test.")
                return

    except Exception as e:
        print(f"Login/Signup Exception: {e}")
        return

    # 2. Upload PDF
    print(f"\nAttempting to upload {PDF_PATH}...")
    if not os.path.exists(PDF_PATH):
        print(f"File {PDF_PATH} not found!")
        return

    try:
        with open(PDF_PATH, 'rb') as f:
            files = {
                'file': (PDF_PATH, f, 'application/pdf')
            }
            data = {
                'content_name': 'Test Upload via Script',
                'source': 'file'
            }
            
            # The session cookies should handle authentication
            resp_upload = session.post(f"{BASE_URL}/api/upload", files=files, data=data)
            
            print(f"Upload Status: {resp_upload.status_code}")
            print(f"Upload Response: {resp_upload.text}")
            
            if resp_upload.ok:
                print("\nSUCCESS: PDF Uploaded and Processed!")
            else:
                print("\nFAILURE: Upload rejected.")

    except Exception as e:
        print(f"Upload Exception: {e}")

if __name__ == "__main__":
    main()
