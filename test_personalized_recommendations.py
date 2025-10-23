#!/usr/bin/env python3
"""
Test script để kiểm tra personalized recommendations
- Mỗi user sẽ có pattern khác nhau
- 8 sản phẩm cùng loại + 2 sản phẩm khác loại
"""

import requests
import json
import time

def test_user_recommendations(user_id, rounds=2):
    """Test recommendations cho một user qua nhiều lần"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING USER {user_id}")
    print(f"{'='*60}")
    
    for round_num in range(1, rounds + 1):
        print(f"\n--- Round {round_num} ---")
        
        try:
            # Call recommendation API
            response = requests.get(f'http://localhost:5002/recommendations/{user_id}', 
                                  params={'num_recs': 10})
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"📊 Total recommendations: {data.get('total', 0)}")
                print(f"🎯 Strategy: {data.get('analysis', {}).get('strategy_used', 'unknown')}")
                print(f"📈 Total interactions: {data.get('analysis', {}).get('total_interactions', 0)}")
                print(f"🗂️ Main category: {data.get('analysis', {}).get('main_category', 'N/A')}")
                
                breakdown = data.get('analysis', {}).get('recommendation_breakdown', {})
                print(f"📋 Breakdown:")
                print(f"   - Same category: {breakdown.get('same_category', 0)}")
                print(f"   - Different categories: {breakdown.get('different_categories', 0)}")
                print(f"   - From history: {breakdown.get('from_history', 0)}")
                print(f"   - From related: {breakdown.get('from_related', 0)}")
                print(f"   - From viewed: {breakdown.get('from_viewed', 0)}")
                
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
                        'price': rec.get('price', 0),
                        'reason': rec.get('reason', 'No reason')
                    })
                
                # Display by category
                for category, products in category_groups.items():
                    print(f"\n   📦 {category} ({len(products)} sản phẩm):")
                    for product in products:
                        print(f"      {product['index']}. {product['name']} - {product['price']:,}đ")
                        print(f"         💡 {product['reason']}")
                
                # Show data source
                data_source = data.get('analysis', {}).get('data_source', 'unknown')
                print(f"\n📍 Data source: {data_source}")
                note = data.get('analysis', {}).get('note', '')
                if note:
                    print(f"📝 Note: {note}")
                    
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        if round_num < rounds:
            print(f"\n⏱️ Waiting 2 seconds before next round...")
            time.sleep(2)

def main():
    """Test multiple users để thấy sự khác biệt"""
    print("🚀 TESTING PERSONALIZED RECOMMENDATION SYSTEM")
    print("Objective: Mỗi user có pattern khác nhau, 8 cùng loại + 2 khác loại")
    
    # Test multiple users
    test_users = [1, 2, 3, 4, 5]
    
    for user_id in test_users:
        test_user_recommendations(user_id, rounds=2)
        
        if user_id < max(test_users):
            print(f"\n{'⏸️ '*20}")
            time.sleep(1)
    
    print(f"\n{'🎉'*30}")
    print("✅ TESTING COMPLETED!")
    print("Check if each user has different recommendations and patterns!")
    print(f"{'🎉'*30}")

if __name__ == "__main__":
    main()