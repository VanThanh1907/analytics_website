#!/usr/bin/env python3
"""
Force test User 3 specifically với detailed output
"""

import requests

def force_test_user_3():
    """Force test User 3"""
    print("🎯 FORCE TEST USER 3 - DETAILED")
    print("="*50)
    
    user_id = 3
    api_url = "http://localhost:5002"
    
    # Make request
    response = requests.get(f"{api_url}/recommendations/{user_id}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ API Response successful for User {user_id}")
        print(f"🔥 Instant switch: {data.get('analysis', {}).get('instant_switch', False)}")
        print(f"🗂️ Main category: {data.get('analysis', {}).get('main_category', 'N/A')}")
        
        print(f"\n📝 EXPECTED TO SEE ON WEBSITE:")
        print(f"   Title: 'INSTANT SWITCH cho User 3: 6 từ Đồ gia dụng nhà bếp + 2 từ categories khác'")
        
        print(f"\n🛍️ PRODUCTS THAT SHOULD DISPLAY:")
        
        for i, rec in enumerate(data.get('recommendations', []), 1):
            category = rec.get('category', 'Unknown')
            name = rec.get('name', 'Unknown')
            reason = rec.get('reason', 'No reason')
            
            if 'Đồ gia dụng nhà bếp' in category:
                print(f"   {i:2d}. ✅ {name}")
                print(f"       📦 {category}")
                print(f"       💡 {reason}")
            else:
                print(f"   {i:2d}. 🔄 {name}")
                print(f"       📦 {category} (Different category)")
                print(f"       💡 {reason}")
        
        # Check if user is seeing different data
        print(f"\n🚨 IF YOU SEE DIFFERENT PRODUCTS:")
        print(f"   1. Check you're logged in as testuser")
        print(f"   2. Check you're on 'Gợi ý cho bạn' page")
        print(f"   3. Try Ctrl+F5 to force refresh")
        print(f"   4. Try opening in incognito/private window")
        
        # Show raw JSON for debugging
        print(f"\n🔧 RAW API DATA (for debugging):")
        print(f"   URL: {api_url}/recommendations/{user_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Total recommendations: {len(data.get('recommendations', []))}")
        
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    force_test_user_3()