import requests
import json

# Test login và recommendations cho user vanthanh1
session = requests.Session()

# Login
login_data = {
    'username': 'testuser',
    'password': '123456'  # Known password for testuser
}

print("🔐 Trying to login...")
login_response = session.post('http://localhost:5000/login', data=login_data)
print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    # Test recommendations
    print("\n🔍 Testing recommendations...")
    rec_response = session.get('http://localhost:5000/recommendations')
    print(f"Recommendations status: {rec_response.status_code}")
    
    if "recommendations" in rec_response.text.lower():
        print("✅ Recommendations page loaded successfully")
    else:
        print("❌ Recommendations page failed to load")
        print("Response preview:", rec_response.text[:200])
else:
    print("❌ Login failed")
    print("Response:", login_response.text[:200])