#!/usr/bin/env python3
import requests
import json

def test_recommendation_flow():
    print("🧪 Testing Recommendation Flow")
    print("=" * 50)
    
    # Test 1: API Health
    try:
        response = requests.get("http://localhost:5001/health", timeout=5)
        print(f"✅ API Health: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ API Health failed: {e}")
        return
    
    print("\n" + "-" * 30)
    
    # Test 2: User 1 recommendations
    try:
        response = requests.get("http://localhost:5001/recommendations/1", timeout=5)
        data = response.json()
        print(f"✅ User 1 Recommendations: {response.status_code}")
        print(f"   Strategy: {data.get('analysis', {}).get('strategy_used', 'unknown')}")
        print(f"   Total interactions: {data.get('analysis', {}).get('total_interactions', 0)}")
        print(f"   Recommendations count: {len(data.get('recommendations', []))}")
        
        if data.get('analysis', {}).get('strategy_used') == 'kafka_behavior_based':
            print("   🎯 BEHAVIOR-BASED WORKING!")
        else:
            print("   ⚠️ Still using fallback")
            
    except Exception as e:
        print(f"❌ User 1 recommendations failed: {e}")
    
    print("\n" + "-" * 30)
    
    # Test 3: Web app status
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        print(f"✅ Web App: {response.status_code}")
    except Exception as e:
        print(f"❌ Web App failed: {e}")
    
    print("\n" + "-" * 30)
    
    # Test 4: Call web app recommendation endpoint (would need login)
    print("📝 Note: To test full flow, need to:")
    print("   1. Register/Login on web app")
    print("   2. Visit /recommendations page")
    print("   3. Check browser console for debug logs")

if __name__ == "__main__":
    test_recommendation_flow()