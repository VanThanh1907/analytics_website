import requests
import json

# Test API mới với 10 recommendations
def test_enhanced_recommendations():
    print("🚀 TESTING ENHANCED RECOMMENDATIONS (10 products)")
    print("="*60)
    
    # Test với user có behavior data
    user_id = 1
    url = f"http://localhost:5002/recommendations/{user_id}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            print(f"👤 USER {user_id} RECOMMENDATIONS:")
            print(f"📊 Total: {data.get('total', 0)} products")
            print(f"🎯 Strategy: {data.get('analysis', {}).get('strategy_used', 'Unknown')}")
            print(f"📈 Total interactions: {data.get('analysis', {}).get('total_interactions', 0)}")
            print(f"🗄️ Data source: {data.get('analysis', {}).get('data_source', 'Unknown')}")
            
            print(f"\n🛍️ PRODUCT RECOMMENDATIONS:")
            for i, product in enumerate(data.get('recommendations', []), 1):
                print(f"  {i:2d}. {product['name']}")
                print(f"      💰 {product['price']:,} VND | 📂 {product['category']}")
                print(f"      💡 {product['reason']}")
                print()
            
            print(f"📊 BEHAVIOR ANALYSIS:")
            analysis = data.get('analysis', {})
            
            clicked_cats = analysis.get('top_clicked_categories', {})
            if clicked_cats:
                print(f"🖱️ Top clicked categories:")
                for cat, count in sorted(clicked_cats.items(), key=lambda x: x[1], reverse=True):
                    print(f"    • {cat}: {count} clicks")
            
            viewed_cats = analysis.get('top_viewed_categories', {})
            if viewed_cats:
                print(f"👀 Top viewed categories:")
                for cat, count in sorted(viewed_cats.items(), key=lambda x: x[1], reverse=True):
                    print(f"    • {cat}: {count} views")
            
            strategies = analysis.get('strategies_applied', [])
            if strategies:
                print(f"\n🎯 STRATEGIES APPLIED:")
                for strategy in strategies:
                    print(f"    ✅ {strategy}")
                    
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("🔧 Make sure API server is running on port 5002")

if __name__ == "__main__":
    test_enhanced_recommendations()