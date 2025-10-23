#!/usr/bin/env python3
"""
Test để xác nhận sản phẩm hiển thị đúng
"""

import requests
import time

def test_multiple_users():
    """Test multiple users để xem recommendations"""
    print("🧪 TESTING ALL USERS - INSTANT SWITCH")
    print("="*60)
    
    api_url = "http://localhost:5002"
    
    for user_id in [1, 2, 3, 4]:
        print(f"\n👤 USER {user_id}:")
        print("-" * 30)
        
        try:
            response = requests.get(f"{api_url}/recommendations/{user_id}")
            
            if response.status_code == 200:
                data = response.json()
                analysis = data.get('analysis', {})
                
                main_cat = analysis.get('main_category', 'N/A')
                total_recs = len(data.get('recommendations', []))
                
                print(f"   🗂️ Main category: {main_cat}")
                print(f"   📊 Total recommendations: {total_recs}")
                print(f"   🔥 Instant switch: {analysis.get('instant_switch', False)}")
                
                # Count products by category
                category_count = {}
                for rec in data.get('recommendations', []):
                    cat = rec.get('category', 'Unknown')
                    category_count[cat] = category_count.get(cat, 0) + 1
                
                print(f"   📦 Product breakdown:")
                for cat, count in category_count.items():
                    if cat == main_cat:
                        print(f"      ✅ {cat}: {count} sản phẩm (MAIN)")
                    else:
                        print(f"      🔄 {cat}: {count} sản phẩm")
                
                # Show first 3 products
                print(f"   🛍️ First 3 products:")
                for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                    print(f"      {i}. {rec.get('name', 'Unknown')} ({rec.get('category', 'Unknown')})")
                    
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            
        time.sleep(0.5)
    
    print(f"\n💡 HOW TO VERIFY ON WEBSITE:")
    print(f"   1. Go to http://localhost:5000")
    print(f"   2. Login: testuser / 123456")
    print(f"   3. Click 'Gợi ý cho bạn' in menu")
    print(f"   4. Should see products matching the analysis above")
    print(f"   5. If not matching, try Ctrl+F5 or clear cache")

if __name__ == "__main__":
    test_multiple_users()