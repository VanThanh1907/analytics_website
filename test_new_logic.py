#!/usr/bin/env python3
"""
Test script cho New Recommendation Logic:
8 sản phẩm cùng danh mục + 2 danh mục liên quan
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'recommendation-engine'))

from simple_recommendation import SimpleRecommendationEngine

def test_new_recommendation_logic():
    print("🧪 Testing NEW Recommendation Logic")
    print("🎯 8 sản phẩm cùng danh mục + 2 danh mục liên quan")
    print("=" * 60)
    
    # Initialize engine
    engine = SimpleRecommendationEngine()
    
    # Test with users who have click history
    test_users = [1, 2, 3]
    
    for user_id in test_users:
        print(f"\n🔍 Testing User ID: {user_id}")
        print("-" * 40)
        
        try:
            # Get recommendations với 10 sản phẩm (8 + 2)
            result = engine.get_recommendations_for_user(user_id, num_recs=10)
            
            if result['status'] == 'success':
                print(f"✅ Status: {result['status']}")
                print(f"📊 Strategy: {result['analysis']['strategy_used']}")
                
                if 'strategy_details' in result['analysis']:
                    for detail in result['analysis']['strategy_details']:
                        print(f"📝 {detail}")
                
                latest_click_product = result['analysis'].get('latest_click_product')
                latest_click_category = result['analysis'].get('latest_click_category')
                print(f"🎯 Latest Click: '{latest_click_product}' ({latest_click_category})")
                
                print(f"🔢 Total Recommendations: {result['total']}")
                print(f"👆 Recent Clicks: {result['analysis']['recent_clicks_count']}")
                
                # Phân loại recommendations theo priority
                same_category_count = 0
                related_category_count = 0
                
                if result['recommendations']:
                    print(f"\n🎁 Recommendations Details:")
                    for i, rec in enumerate(result['recommendations'], 1):
                        priority = rec.get('priority', 'unknown')
                        reason = rec.get('reason', 'No reason')
                        
                        if priority == 'same_category':
                            same_category_count += 1
                            print(f"  {i}. 🎯 {rec['name']} - {rec['category']}")
                            print(f"     📝 {reason}")
                        elif priority == 'related_category':
                            related_category_count += 1
                            print(f"  {i}. 🔗 {rec['name']} - {rec['category']}")
                            print(f"     📝 {reason}")
                        else:
                            print(f"  {i}. 📦 {rec['name']} - {rec['category']}")
                            print(f"     📝 {reason}")
                
                print(f"\n📊 Breakdown:")
                print(f"  🎯 Same Category Products: {same_category_count}")
                print(f"  🔗 Related Category Products: {related_category_count}")
                print(f"  📦 Others: {len(result['recommendations']) - same_category_count - related_category_count}")
                
                # Kiểm tra logic
                if same_category_count > 0 and latest_click_category:
                    print(f"✅ LOGIC CHECK: Found products from same category '{latest_click_category}'")
                if related_category_count > 0:
                    print(f"✅ LOGIC CHECK: Found products from related categories")
                
            else:
                print(f"❌ Error: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception for User {user_id}: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Test completed! Check if new logic works:")
    print("   Expected: 8 products from same category + 2 from related categories")

if __name__ == "__main__":
    test_new_recommendation_logic()