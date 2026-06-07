"""Quick test of auth endpoint"""
import requests, sys
try:
    r = requests.post('http://127.0.0.1:8000/api/auth/register', 
        json={'username':'test','email':'test@test.com','password':'123'})
    print('Status:', r.status_code)
    print('Body:', r.text[:500])
except Exception as e:
    print('ERROR:', e)
    sys.exit(1)
