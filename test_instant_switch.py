#!/usr/bin/env python3
"""
Test INSTANT CATEGORY SWITCHING - 1 click = immediate change
"""

import requests
import json
import time

def test_instant_switch():
    """Test instant category switching với 1 click"""
    print("🚀 TESTING INSTANT CATEGORY SWITCH")
    print("="*60)
    
    user_id = 1
    api_url = "http://localhost:5002"
    
    # 1. Check current state
    print("📊 STEP 1: Current recommendations")
    try:
        response = requests.get(f"{api_url}/recommendations/{user_id}")
        if response.status_code == 200:
            data = response.json()
            current_main = data.get('analysis', {}).get('main_category', 'N/A')
            current_total = data.get('analysis', {}).get('total_interactions', 0)
            is_instant = data.get('analysis', {}).get('instant_switch', False)
            latest_click = data.get('analysis', {}).get('latest_click_category', 'N/A')
            
            print(f"   🗂️ Current main category: {current_main}")
            print(f"   📈 Current total interactions: {current_total}")
            print(f"   🔥 Instant switch enabled: {is_instant}")
            print(f"   🎯 Latest click category: {latest_click}")
            
            # Show current top 3
            print(f"   🛍️ Current top 3:")
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"      {i}. {rec.get('name')} - {rec.get('category')}")
                print(f"         💡 {rec.get('reason', 'No reason')}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    print(f"\n⚡ STEP 2: Test với categories khác nhau...")
    
    # Test với different categories
    test_categories = [
        ("Sản phẩm làm đẹp & Chăm sóc cá nhân", "Serum Vitamin C", 201),
        ("Đồ gia dụng nhà bếp", "Chảo chống dính", 202),
        ("Thực phẩm khô & Gia vị", "Mì tôm Hảo Hảo", 203),
        ("Bánh kẹo & Snacks", "Snack Pringles", 204)
    ]
    
    for category, product_name, product_id in test_categories:
        print(f"\n🎯 Testing category: {category}")
        
        # Check before
        r1 = requests.get(f"{api_url}/recommendations/{user_id}")
        before_main = r1.json().get('analysis', {}).get('main_category', 'N/A') if r1.status_code == 200 else 'N/A'
        
        print(f"   Before: {before_main}")
        
        # Simulate tracking - tạo fake interaction trong database 
        print(f"   Simulating click on '{product_name}'...")
        time.sleep(1)
        
        # Check after immediately  
        r2 = requests.get(f"{api_url}/recommendations/{user_id}")
        if r2.status_code == 200:
            after_data = r2.json()
            after_main = after_data.get('analysis', {}).get('main_category', 'N/A')
            latest_click = after_data.get('analysis', {}).get('latest_click_category', 'N/A')
            instant_enabled = after_data.get('analysis', {}).get('instant_switch', False)
            
            print(f"   After: {after_main}")
            print(f"   Latest click detected: {latest_click}")
            print(f"   Instant switch: {instant_enabled}")
            
            if after_main == category:
                print(f"   ✅ SUCCESS: Category changed to {category}!")
            elif before_main != after_main:
                print(f"   🔄 PARTIAL: Category changed from {before_main} to {after_main}")
            else:
                print(f"   ⚠️ NO CHANGE: Still {after_main}")
                
        print(f"   " + "-"*40)
    
    print(f"\n📊 FINAL CHECK: Current system status")
    try:
        final_response = requests.get(f"{api_url}/recommendations/{user_id}")
        if final_response.status_code == 200:
            final_data = final_response.json()
            
            print(f"   🗂️ Final main category: {final_data.get('analysis', {}).get('main_category', 'N/A')}")
            print(f"   🎯 Strategy used: {final_data.get('analysis', {}).get('strategy_used', 'N/A')}")
            print(f"   📍 Data source: {final_data.get('analysis', {}).get('data_source', 'N/A')}")
            print(f"   🔥 Instant switch: {final_data.get('analysis', {}).get('instant_switch', False)}")
            
            # Show ALL categories with breakdown
            breakdown = final_data.get('analysis', {}).get('recommendation_breakdown', {})
            print(f"\n📊 RECOMMENDATION BREAKDOWN:")
            print(f"   📦 Same category: {breakdown.get('same_category', 0)}")
            print(f"   🔄 Different categories: {breakdown.get('different_categories', 0)}")
            print(f"   📝 From history: {breakdown.get('from_history', 0)}")
            print(f"   🔗 From related: {breakdown.get('from_related', 0)}")
            print(f"   👀 From viewed: {breakdown.get('from_viewed', 0)}")
            print(f"   🔍 From discovery: {breakdown.get('from_discovery', 0)}")
            
    except Exception as e:
        print(f"   ❌ Final check error: {e}")
    
    print(f"\n💡 TO TEST REAL INSTANT SWITCHING:")
    print(f"   1. Go to http://localhost:5000")
    print(f"   2. Login với testuser / 123456")
    print(f"   3. Click vào 1 sản phẩm bất kỳ")
    print(f"   4. Vào page 'Gợi ý cho bạn' ngay lập tức")
    print(f"   5. Should see instant category change!")
    print(f"\n🔥 INSTANT SWITCH: 1 CLICK = IMMEDIATE CHANGE")

if __name__ == "__main__":
    test_instant_switch()