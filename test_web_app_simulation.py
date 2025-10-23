#!/usr/bin/env python3
"""
Web App Debug Test - Simulate exact web app flow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'recommendation-engine'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'web-app'))

from simple_recommendation import SimpleRecommendationEngine

# Simulate web app Product class
class Product:
    def __init__(self, id, name, description, price, category, image_url, stock):
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.image_url = image_url
        self.stock = stock

def simulate_web_app_recommendations_route():
    """Simulate exactly what happens in web app recommendations route"""
    
    print("🎭 SIMULATING WEB APP RECOMMENDATIONS ROUTE")
    print("=" * 60)
    
    # User ID (simulate current_user.id)
    user_id = 1
    
    # Initialize engine (simulate web app engine)
    recommendation_engine = SimpleRecommendationEngine()
    
    recommendations = []
    analysis_data = {}
    
    print(f"🔍 Getting recommendations for user ID: {user_id}")
    
    # API server not available in this test, go directly to engine
    try:
        print("🔄 Trying direct recommendation engine...")
        result = recommendation_engine.get_recommendations_for_user(user_id, 10)  # 8 + 2
        
        if result['status'] == 'success' and result['recommendations']:
            recommendations = result['recommendations']
            analysis_data = result.get('analysis', {})
            print(f"✅ Direct engine recommendations: {len(recommendations)} sản phẩm")
            print(f"🔍 DEBUG - Strategy: {analysis_data.get('strategy_used')}")
            print(f"🔍 DEBUG - Latest click product: {analysis_data.get('latest_click_product')}")
            
            print("\n🔧 SIMULATING WEB APP DATA CONVERSION:")
            print("-" * 50)
            
            # IMPORTANT: Ensure product objects have priority and reason attributes
            for i, rec in enumerate(recommendations):
                if isinstance(rec, dict):
                    print(f"📦 Processing recommendation {i+1}:")
                    print(f"   Dict keys: {list(rec.keys())}")
                    print(f"   Original priority: {rec.get('priority')}")
                    print(f"   Original reason: {rec.get('reason')}")
                    
                    # Convert dict to Product-like object with additional attributes
                    # Simulate Product.query.get(rec['id']) by creating Product object
                    product = Product(
                        id=rec['id'],
                        name=rec['name'],
                        description=rec['description'],
                        price=rec['price'],
                        category=rec['category'],
                        image_url=rec['image_url'],
                        stock=rec['stock']
                    )
                    
                    if product:
                        # Add priority and reason attributes
                        product.priority = rec.get('priority', 'unknown')
                        product.reason = rec.get('reason', 'No reason provided')
                        recommendations[i] = product
                        
                        print(f"   ✅ Converted to Product object:")
                        print(f"   - ID: {product.id}")
                        print(f"   - Name: {product.name}")
                        print(f"   - Priority: {product.priority}")
                        print(f"   - Reason: {product.reason}")
                        print()
                
            print("🎯 FINAL TEMPLATE DATA:")
            print("-" * 50)
            print(f"📊 Analysis data strategy: {analysis_data.get('strategy_used')}")
            print(f"📊 Latest click product: {analysis_data.get('latest_click_product')}")
            print(f"📦 Recommendations count: {len(recommendations)}")
            
            print("\n🎨 TEMPLATE DATA STRUCTURE:")
            print("-" * 50)
            for i, product in enumerate(recommendations[:3]):  # Show first 3
                print(f"Product {i+1} for template:")
                print(f"  - Type: {type(product)}")
                print(f"  - Has priority attr: {hasattr(product, 'priority')}")
                print(f"  - Has reason attr: {hasattr(product, 'reason')}")
                if hasattr(product, 'priority'):
                    print(f"  - Priority value: {product.priority}")
                if hasattr(product, 'reason'):
                    print(f"  - Reason value: {product.reason}")
                print()
                
    except Exception as e:
        print(f"❌ Error in simulation: {e}")
        import traceback
        traceback.print_exc()
    
    return recommendations, analysis_data

if __name__ == "__main__":
    simulate_web_app_recommendations_route()