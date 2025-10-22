import requests
import json

# Tạo session mới và login
session = requests.Session()

print("🔐 Login với testuser...")
login_data = {
    'username': 'testuser',
    'password': '123456'
}

# Post login
login_resp = session.post('http://localhost:5000/login', data=login_data, allow_redirects=False)
print(f"Login response: {login_resp.status_code}")

if 'location' in login_resp.headers:
    print(f"Redirect to: {login_resp.headers['location']}")

# Get recommendations page
print("\n🔍 Getting recommendations...")
rec_resp = session.get('http://localhost:5000/recommendations')
print(f"Recommendations status: {rec_resp.status_code}")

if 'Gợi ý' in rec_resp.text:
    print("✅ Found recommendations page")
    if 'Gạo ST25' in rec_resp.text:
        print("✅ Found Gạo ST25 in recommendations!")
    else:
        print("❌ No Gạo ST25 found")
        # Check for empty recommendations message
        if 'Chưa có dữ liệu' in rec_resp.text:
            print("⚠️ Shows 'no data' message")
elif 'Đăng nhập' in rec_resp.text:
    print("❌ Redirected to login page - auth failed")
else:
    print("❌ Unknown page")
    print("Page title:", rec_resp.text[:200])