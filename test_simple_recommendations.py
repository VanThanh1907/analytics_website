#!/usr/bin/env python3
"""
Test script cho Simple Recommendation Engine
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'recommendation-engine'))

from simple_recommendation import SimpleRecommendationEngine

def test_simple_engine():
    print("🧪 Testing Simple Recommendation Engine with Latest Click Priority")
    print("=" * 60)
    
    # Initialize engine
    engine = SimpleRecommendationEngine()
    
    # Test with different user IDs
    test_users = [1, 2, 3]
    
    for user_id in test_users:
        print(f"\n🔍 Testing User ID: {user_id}")
        print("-" * 40)
        
        try:
            # Get recommendations
            result = engine.get_recommendations_for_user(user_id, num_recs=6)
            
            if result['status'] == 'success':
                print(f"✅ Status: {result['status']}")
                print(f"📊 Strategy: {result['analysis']['strategy_used']}")
                
                if 'strategy_details' in result['analysis']:
                    print(f"📝 Details: {', '.join(result['analysis']['strategy_details'])}")
                
                latest_click = result['analysis'].get('latest_click_category')
                print(f"🎯 Latest Click Category: {latest_click or 'None'}")
                
                print(f"🔢 Total Recommendations: {result['total']}")
                print(f"🤝 Total Interactions: {result['analysis']['total_interactions']}")
                print(f"👆 Recent Clicks: {result['analysis']['recent_clicks_count']}")
                print(f"👀 Recent Interactions: {result['analysis']['recent_interactions_count']}")
                
                # Show recommendations
                if result['recommendations']:
                    print(f"\n🎁 Top 3 Recommendations:")
                    for i, rec in enumerate(result['recommendations'][:3], 1):
                        reason = rec.get('reason', 'No reason')
                        priority = rec.get('priority', 'normal')
                        print(f"  {i}. {rec['name']} (ID: {rec['id']}) - {rec['category']}")
                        print(f"     💡 Reason: {reason}")
                        print(f"     🏆 Priority: {priority}")
                else:
                    print("🚫 No recommendations found")
                
                # Show category analysis
                if result['analysis']['top_clicked_categories']:
                    print(f"\n📊 Top Clicked Categories:")
                    for cat, count in result['analysis']['top_clicked_categories'].items():
                        print(f"  - {cat}: {count} clicks")
                
            else:
                print(f"❌ Error: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception for User {user_id}: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Test completed! Check if latest click priority is working.")

if __name__ == "__main__":
    test_simple_engine()