#!/usr/bin/env python3
"""
Debug Web App Data Flow - Specific Issue
Kiểm tra xem sao data từ engine không hiển thị trong web app
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'recommendation-engine'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'web-app'))

from simple_recommendation import SimpleRecommendationEngine

print("🔍 DEBUG: Testing SimpleRecommendationEngine data structure")
print("=" * 60)

try:
    # Initialize engine
    engine = SimpleRecommendationEngine()
    
    # Test with user 1
    user_id = 1
    print(f"🧪 Testing user {user_id}")
    
    # Get recommendations
    result = engine.get_recommendations_for_user(user_id, 10)
    
    print(f"📊 Engine result status: {result.get('status')}")
    print(f"📊 Strategy: {result.get('analysis', {}).get('strategy_used')}")
    print(f"📊 Recommendations count: {len(result.get('recommendations', []))}")
    
    recommendations = result.get('recommendations', [])
    
    print("\n🔍 DETAILED RECOMMENDATION STRUCTURE:")
    print("-" * 50)
    
    for i, rec in enumerate(recommendations[:3]):  # Show first 3
        print(f"Recommendation {i+1}:")
        print(f"  Type: {type(rec)}")
        if isinstance(rec, dict):
            print(f"  Keys: {list(rec.keys())}")
            print(f"  ID: {rec.get('id')}")
            print(f"  Name: {rec.get('name')}")
            print(f"  Priority: {rec.get('priority')}")
            print(f"  Reason: {rec.get('reason')}")
        else:
            print(f"  Object attributes: {dir(rec)}")
            if hasattr(rec, 'id'):
                print(f"  ID: {rec.id}")
            if hasattr(rec, 'name'):
                print(f"  Name: {rec.name}")
            if hasattr(rec, 'priority'):
                print(f"  Priority: {rec.priority}")
            if hasattr(rec, 'reason'):
                print(f"  Reason: {rec.reason}")
        print()
    
    print("\n🎯 PROBLEM DIAGNOSIS:")
    print("-" * 50)
    
    # Check if recommendations are dicts or objects
    if recommendations:
        first_rec = recommendations[0]
        if isinstance(first_rec, dict):
            print("✅ Engine returns dictionaries - Web app conversion should work")
            print("❓ Issue might be in web app template or data passing")
        else:
            print("❌ Engine returns objects - Need to check object structure")
            print("❓ Web app expects dictionaries for conversion")
    
    # Check analysis data
    analysis = result.get('analysis', {})
    print(f"\n📈 Analysis data keys: {list(analysis.keys())}")
    print(f"📈 Strategy used: {analysis.get('strategy_used')}")
    print(f"📈 Latest click product: {analysis.get('latest_click_product')}")
    
    print("\n💡 NEXT STEPS:")
    print("-" * 50)
    print("1. Verify engine returns correct dict format")
    print("2. Check web app conversion logic")
    print("3. Test template data passing")
    print("4. Verify template rendering logic")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()