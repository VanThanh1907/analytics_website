#!/usr/bin/env python3
"""
Debug INSTANT SWITCH - kiểm tra tại sao sản phẩm không khớp với category
"""

import requests
import json

def debug_user_3_recommendations():
    """Debug chi tiết User 3 recommendations"""
    print("🔍 DEBUGGING USER 3 INSTANT SWITCH")
    print("="*60)
    
    user_id = 3
    api_url = "http://localhost:5002"
    
    try:
        # Get recommendations
        response = requests.get(f"{api_url}/recommendations/{user_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 USER {user_id} ANALYSIS:")
            analysis = data.get('analysis', {})
            
            print(f"   🗂️ Main category: {analysis.get('main_category', 'N/A')}")
            print(f"   🔥 Instant switch: {analysis.get('instant_switch', False)}")
            print(f"   🎯 Latest click category: {analysis.get('latest_click_category', 'N/A')}")
            print(f"   📍 Data source: {analysis.get('data_source', 'N/A')}")
            print(f"   📈 Total interactions: {analysis.get('total_interactions', 0)}")
            
            # Show clicked categories
            clicked_cats = analysis.get('top_clicked_categories', {})
            print(f"\n🖱️ CLICKED CATEGORIES:")
            for cat, score in sorted(clicked_cats.items(), key=lambda x: x[1], reverse=True):
                print(f"   📦 {cat}: {score} points")
            
            # Show breakdown
            breakdown = analysis.get('recommendation_breakdown', {})
            print(f"\n📊 RECOMMENDATION BREAKDOWN:")
            print(f"   📦 Same category: {breakdown.get('same_category', 0)}")
            print(f"   🔄 Different categories: {breakdown.get('different_categories', 0)}")
            print(f"   📝 From history: {breakdown.get('from_history', 0)}")
            print(f"   🔗 From related: {breakdown.get('from_related', 0)}")
            print(f"   👀 From viewed: {breakdown.get('from_viewed', 0)}")
            
            # Show ALL recommendations with categories
            print(f"\n🛍️ ALL {len(data.get('recommendations', []))} RECOMMENDATIONS:")
            category_count = {}
            
            for i, rec in enumerate(data.get('recommendations', []), 1):
                category = rec.get('category', 'Unknown')
                category_count[category] = category_count.get(category, 0) + 1
                
                print(f"   {i:2d}. {rec.get('name', 'Unknown')}")
                print(f"       📦 Category: {category}")
                print(f"       💡 Reason: {rec.get('reason', 'No reason')}")
                print(f"       💰 Price: {rec.get('price', 0):,} VND")
                print()
            
            print(f"📊 CATEGORY SUMMARY:")
            for cat, count in category_count.items():
                print(f"   📦 {cat}: {count} sản phẩm")
            
            # Check if main category matches actual products
            main_cat = analysis.get('main_category')
            main_cat_count = category_count.get(main_cat, 0)
            
            print(f"\n🔍 VALIDATION:")
            print(f"   Expected main category: {main_cat}")
            print(f"   Actual products from main category: {main_cat_count}")
            
            if main_cat_count >= 6:
                print(f"   ✅ CORRECT: Found {main_cat_count} products from {main_cat}")
            else:
                print(f"   ❌ MISMATCH: Only {main_cat_count} products from {main_cat}, expected 6+")
                print(f"   🔧 This indicates a logic error in recommendation generation")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    debug_user_3_recommendations()