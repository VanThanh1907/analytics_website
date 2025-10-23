#!/usr/bin/env python3
"""
Debug category filtering để tìm vấn đề mismatch giữa title và products
"""

import requests

def debug_category_filtering():
    """Debug category filtering issue"""
    print("🔍 DEBUG CATEGORY FILTERING - Title vs Products Mismatch")
    print("="*70)
    
    api_url = "http://localhost:5002"
    
    # Test User 1 specifically (từ ảnh có vấn đề)
    user_id = 1
    
    print(f"🧪 DEBUGGING USER {user_id}:")
    print("-" * 40)
    
    try:
        response = requests.get(f"{api_url}/recommendations/{user_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            # ✅ ANALYSIS INFO
            analysis = data.get('analysis', {})
            main_category = analysis.get('main_category', 'Unknown')
            note = analysis.get('note', 'No note')
            debug_info = analysis.get('debug_info', {})
            
            print(f"📊 Analysis note: {note}")
            print(f"🎯 Main category: '{main_category}'")
            
            if debug_info:
                print(f"🔧 Debug info:")
                print(f"   Available main products: {debug_info.get('available_main_products', 0)}")
                print(f"   Target main products: {debug_info.get('target_main_products', 0)}")
                print(f"   Final main products: {debug_info.get('final_main_products', 0)}")
                print(f"   Categories in result: {debug_info.get('all_categories_in_result', [])}")
            
            # ✅ CHECK PRODUCTS VS CATEGORY
            recommendations = data.get('recommendations', [])
            
            print(f"\n🛍️ ACTUAL PRODUCTS ({len(recommendations)} total):")
            
            category_counts = {}
            for i, product in enumerate(recommendations, 1):
                category = product.get('category', 'Unknown')
                name = product.get('name', 'Unknown')
                reason = product.get('reason', 'No reason')
                
                # Count by category
                category_counts[category] = category_counts.get(category, 0) + 1
                
                # Show with highlighting
                if category == main_category:
                    icon = "✅"
                else:
                    icon = "❌"
                    
                print(f"   {i:2d}. {icon} {name}")
                print(f"       📦 Category: {category}")
                print(f"       💡 Reason: {reason}")
            
            print(f"\n📊 CATEGORY BREAKDOWN:")
            for category, count in category_counts.items():
                if category == main_category:
                    print(f"   ✅ {category}: {count} products (MAIN - SHOULD BE MAJORITY)")
                else:
                    print(f"   🔄 {category}: {count} products (Other)")
            
            # ✅ VALIDATION
            main_count = category_counts.get(main_category, 0)
            total_other = sum(count for cat, count in category_counts.items() if cat != main_category)
            
            print(f"\n🎯 VALIDATION:")
            print(f"   Main category products: {main_count}")
            print(f"   Other category products: {total_other}")
            
            if main_count >= 6:  # Should be at least 6-8 products from main category
                print(f"   ✅ PASS: Enough main category products")
            else:
                print(f"   ❌ FAIL: Not enough main category products")
                print(f"   🔧 ISSUE: Title says '{main_category}' but products don't match!")
                
            # Check if title matches reality
            expected_pattern = f"{main_count} từ {main_category}"
            if expected_pattern in note:
                print(f"   ✅ PASS: Title matches actual products")
            else:
                print(f"   ❌ FAIL: Title doesn't match actual products")
                print(f"   📝 Title says: {note}")
                print(f"   🛍️ Reality: {main_count} từ {main_category}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n🚀 DEBUG COMPLETE")
    print("="*70)

if __name__ == "__main__":
    debug_category_filtering()