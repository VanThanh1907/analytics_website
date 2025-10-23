#!/usr/bin/env python3
"""Test User 2 recommendations sau khi thêm beauty products"""

import requests
import json

def test_user_2():
    print("🧪 Testing User 2 - Should have beauty products now")
    
    try:
        response = requests.get('http://localhost:5002/recommendations/2', 
                              params={'num_recs': 10})
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 Total recommendations: {data.get('total', 0)}")
            print(f"🗂️ Main category: {data.get('analysis', {}).get('main_category', 'N/A')}")
            
            breakdown = data.get('analysis', {}).get('recommendation_breakdown', {})
            print(f"📋 Breakdown:")
            print(f"   - Same category: {breakdown.get('same_category', 0)}")
            print(f"   - Different categories: {breakdown.get('different_categories', 0)}")
            
            print(f"\n🛍️ RECOMMENDATIONS:")
            
            # Group by category
            category_groups = {}
            for i, rec in enumerate(data.get('recommendations', []), 1):
                category = rec.get('category', 'Unknown')
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append({
                    'index': i,
                    'name': rec.get('name', 'Unknown'),
                    'price': rec.get('price', 0)
                })
            
            # Display by category
            for category, products in category_groups.items():
                print(f"\n   📦 {category} ({len(products)} sản phẩm):")
                for product in products:
                    print(f"      {product['index']}. {product['name']} - {product['price']:,}đ")
            
            # Check if beauty products are included
            beauty_products = category_groups.get('Sản phẩm làm đẹp & Chăm sóc cá nhân', [])
            if beauty_products:
                print(f"\n✅ SUCCESS: Found {len(beauty_products)} beauty products!")
            else:
                print(f"\n❌ ISSUE: No beauty products found!")
                
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_user_2()