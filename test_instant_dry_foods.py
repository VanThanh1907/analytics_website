#!/usr/bin/env python3
"""
Test INSTANT recommendations khi user click vào Thực phẩm khô & Gia vị
"""

import requests
import json
import time

def simulate_clicks_and_check():
    """Simulate clicking và kiểm tra instant updates"""
    print("🚀 TESTING INSTANT UPDATES - Thực phẩm khô & Gia vị")
    print("="*60)
    
    user_id = 1
    
    # 1. Check current state
    print("📊 STEP 1: Current recommendations")
    try:
        response = requests.get(f'http://localhost:5002/recommendations/{user_id}')
        if response.status_code == 200:
            data = response.json()
            current_main = data.get('analysis', {}).get('main_category', 'N/A')
            current_total = data.get('analysis', {}).get('total_interactions', 0)
            
            print(f"   🗂️ Current main category: {current_main}")
            print(f"   📈 Current total interactions: {current_total}")
            
            # Show current top 3
            print(f"   🛍️ Current top 3:")
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"      {i}. {rec.get('name')} - {rec.get('category')}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    print(f"\n⚡ STEP 2: Simulate clicking on Thực phẩm khô & Gia vị products...")
    print("   (In reality, user would click on website)")
    print("   Now checking recommendations again...")
    
    time.sleep(1)
    
    # 2. Check immediately after
    print(f"\n📊 STEP 3: Check recommendations for changes")
    try:
        response = requests.get(f'http://localhost:5002/recommendations/{user_id}')
        if response.status_code == 200:
            data = response.json()
            new_main = data.get('analysis', {}).get('main_category', 'N/A')
            new_total = data.get('analysis', {}).get('total_interactions', 0)
            
            print(f"   🗂️ New main category: {new_main}")
            print(f"   📈 New total interactions: {new_total}")
            print(f"   🔄 Is real-time: {data.get('analysis', {}).get('is_real_time', False)}")
            
            # Show ALL products with categories
            print(f"\n🛍️ ALL 10 RECOMMENDATIONS:")
            category_count = {}
            
            for i, rec in enumerate(data.get('recommendations', []), 1):
                category = rec.get('category', 'Unknown')
                category_count[category] = category_count.get(category, 0) + 1
                
                print(f"   {i}. {rec.get('name')} - {category}")
                print(f"      💡 {rec.get('reason', 'No reason')}")
            
            print(f"\n📊 CATEGORY BREAKDOWN:")
            for cat, count in category_count.items():
                print(f"   📦 {cat}: {count} sản phẩm")
            
            # Check if we have Thực phẩm khô & Gia vị
            kho_gia_vi_count = category_count.get('Thực phẩm khô & Gia vị', 0)
            if kho_gia_vi_count > 0:
                print(f"\n✅ SUCCESS: Found {kho_gia_vi_count} Thực phẩm khô & Gia vị products!")
            else:
                print(f"\n⚠️ ISSUE: No Thực phẩm khô & Gia vị products found!")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n💡 TO TEST REAL INSTANT UPDATES:")
    print(f"   1. Go to http://localhost:5000")
    print(f"   2. Click on products in 'Thực phẩm khô' category") 
    print(f"   3. Run this script again immediately")
    print(f"   4. Should see main category change to 'Thực phẩm khô & Gia vị'")

if __name__ == "__main__":
    simulate_clicks_and_check()