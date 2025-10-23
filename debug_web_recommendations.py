#!/usr/bin/env python3
"""
Debug script để kiểm tra recommendation data thực tế
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'recommendation-engine'))

from simple_recommendation import SimpleRecommendationEngine

def debug_web_app_data():
    print("🔍 DEBUG: Web App Recommendation Data")
    print("=" * 50)
    
    engine = SimpleRecommendationEngine()
    
    # Test với user 1 như trong web app
    user_id = 1
    print(f"Testing User ID: {user_id}")
    
    try:
        # Get recommendations như web app
        result = engine.get_recommendations_for_user(user_id, num_recs=10)
        
        print(f"\n📊 Status: {result['status']}")
        print(f"📈 Strategy: {result['analysis']['strategy_used']}")
        
        if 'strategy_details' in result['analysis']:
            print(f"📝 Strategy Details:")
            for detail in result['analysis']['strategy_details']:
                print(f"  - {detail}")
        
        print(f"🎯 Latest Click Product: {result['analysis'].get('latest_click_product', 'None')}")
        print(f"🎯 Latest Click Category: {result['analysis'].get('latest_click_category', 'None')}")
        print(f"👆 Recent Clicks Count: {result['analysis']['recent_clicks_count']}")
        print(f"🔢 Total Recommendations: {result['total']}")
        
        # Show recommendations với priority
        print(f"\n🎁 Recommendations (with priority):")
        for i, rec in enumerate(result['recommendations'], 1):
            priority = rec.get('priority', 'unknown')
            reason = rec.get('reason', 'No reason')
            
            priority_icon = {
                'same_category': '🎯',
                'related_category': '🔗', 
                'viewed_category': '👁️',
                'fallback': '📦'
            }.get(priority, '❓')
            
            print(f"  {i}. {priority_icon} {rec['name']} ({rec['category']})")
            print(f"     Priority: {priority}")
            print(f"     Reason: {reason}")
        
        # Check if this matches what web app should receive
        print(f"\n✅ This is the data web app should receive!")
        print(f"   - Template should show: '{result['analysis']['strategy_used']}'")
        print(f"   - Products should have priority colors")
        print(f"   - Latest click should be shown: '{result['analysis'].get('latest_click_product', 'None')}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_web_app_data()