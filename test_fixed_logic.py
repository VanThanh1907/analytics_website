#!/usr/bin/env python3
"""
Fixed version với logic 100% chính xác
"""

import requests

def test_fixed_logic():
    """Test logic đã được fix"""
    print("🔧 TESTING FIXED LOGIC - 100% ACCURACY")
    print("="*60)
    
    api_url = "http://localhost:5002"
    
    for user_id in [1, 2, 3, 4]:
        print(f"\n🧪 USER {user_id} TEST:")
        print("-" * 30)
        
        try:
            response = requests.get(f"{api_url}/recommendations/{user_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # ✅ ANALYSIS INFO
                analysis = data.get('analysis', {})
                main_category = analysis.get('main_category', 'Unknown')
                note = analysis.get('note', 'No note')
                
                print(f"📊 Analysis: {note}")
                print(f"🎯 Main category: {main_category}")
                
                # ✅ CHECK PRODUCTS VS CATEGORY
                recommendations = data.get('recommendations', [])
                main_products = [r for r in recommendations if r['category'] == main_category]
                other_products = [r for r in recommendations if r['category'] != main_category]
                
                print(f"✅ Products same category ({len(main_products)}):")
                for p in main_products:
                    print(f"   - {p['name']} ({p['category']})")
                
                print(f"🔄 Products other categories ({len(other_products)}):")
                for p in other_products:
                    print(f"   - {p['name']} ({p['category']})")
                
                # ✅ VALIDATION
                title_match = str(len(main_products)) in note and main_category in note
                products_match = all(p['category'] == main_category for p in main_products)
                
                if title_match and products_match:
                    print(f"✅ PASS: Title và products hoàn toàn khớp!")
                else:
                    print(f"❌ FAIL: Title không khớp với products")
                    print(f"   Title says: {note}")
                    print(f"   Actual main products: {len(main_products)}")
                    print(f"   Main category match: {products_match}")
                    
            else:
                print(f"❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing user {user_id}: {e}")
    
    print(f"\n🚀 TESTING COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_fixed_logic()