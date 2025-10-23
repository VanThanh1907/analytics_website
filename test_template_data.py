#!/usr/bin/env python3
"""
Test script để verify data flow from engine to template
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'recommendation-engine'))

from simple_recommendation import SimpleRecommendationEngine

def simulate_web_app_flow():
    print("🧪 Simulating Web App Data Flow")
    print("=" * 50)
    
    engine = SimpleRecommendationEngine()
    user_id = 1  # Simulate logged in user
    
    try:
        # Step 1: Get recommendations như web app
        result = engine.get_recommendations_for_user(user_id, num_recs=10)
        
        if result['status'] == 'success':
            recommendations = result['recommendations']
            analysis_data = result.get('analysis', {})
            
            print(f"✅ Engine returned {len(recommendations)} recommendations")
            print(f"📊 Strategy: {analysis_data.get('strategy_used')}")
            print(f"🎯 Latest Click Product: {analysis_data.get('latest_click_product')}")
            
            # Step 2: Simulate template data processing
            print(f"\n📝 Template Data Check:")
            print(f"  - analysis.strategy_used = '{analysis_data.get('strategy_used')}'")
            print(f"  - analysis.latest_click_product = '{analysis_data.get('latest_click_product')}'")
            print(f"  - len(products) = {len(recommendations)}")
            
            # Step 3: Check product data structure
            print(f"\n🎁 Product Data Structure:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  Product {i}:")
                print(f"    - name: {rec.get('name')}")
                print(f"    - category: {rec.get('category')}")
                print(f"    - priority: {rec.get('priority', 'MISSING!')}")
                print(f"    - reason: {rec.get('reason', 'MISSING!')}")
            
            # Step 4: Simulate template logic
            print(f"\n🎨 Template Logic Simulation:")
            
            if analysis_data.get('strategy_used') == 'same_category_plus_related':
                print("  ✅ Template should show: '8 sản phẩm cùng danh mục + 2 danh mục liên quan'")
                print(f"  ✅ Should show latest click: '{analysis_data.get('latest_click_product')}'")
            else:
                print(f"  ❌ Unexpected strategy: {analysis_data.get('strategy_used')}")
            
            # Count by priority
            priority_count = {}
            for rec in recommendations:
                priority = rec.get('priority', 'unknown')
                priority_count[priority] = priority_count.get(priority, 0) + 1
            
            print(f"\n📊 Priority Distribution:")
            for priority, count in priority_count.items():
                color = {
                    'same_category': 'GREEN (success)',
                    'related_category': 'BLUE (info)',
                    'unknown': 'YELLOW (warning)'
                }.get(priority, 'DEFAULT')
                print(f"  - {priority}: {count} products ({color} header)")
            
            # Check if data is ready for template
            print(f"\n🎯 Template Ready Check:")
            if all(rec.get('priority') for rec in recommendations):
                print("  ✅ All products have priority → Headers will show colors")
            else:
                print("  ❌ Some products missing priority → Will show default yellow")
                
            if all(rec.get('reason') for rec in recommendations):
                print("  ✅ All products have reasons → Will show detailed explanations")
            else:
                print("  ❌ Some products missing reasons → Will show generic text")
            
        else:
            print(f"❌ Engine failed: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    simulate_web_app_flow()