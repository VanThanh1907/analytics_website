#!/usr/bin/env python3
"""
Test script để kiểm tra REAL-TIME recommendation updates
- Test user clicks vào sản phẩm
- Kiểm tra recommendations có thay đổi ngay lập tức không
"""

import requests
import json
import time

def test_real_time_updates():
    """Test real-time recommendation updates"""
    print("🚀 TESTING REAL-TIME RECOMMENDATION UPDATES")
    print("Objective: Kiểm tra hệ thống cập nhật ngay lập tức khi user click")
    
    user_id = 1  # Test với user 1
    
    print(f"\n{'='*60}")
    print(f"🧪 TESTING USER {user_id} - REAL-TIME UPDATES")
    print(f"{'='*60}")
    
    # Test 1: Lấy recommendations ban đầu
    print(f"\n--- TEST 1: Initial Recommendations ---")
    
    try:
        response = requests.get(f'http://localhost:5002/recommendations/{user_id}', 
                              params={'num_recs': 10})
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 Total recommendations: {data.get('total', 0)}")
            print(f"🗂️ Main category: {data.get('analysis', {}).get('main_category', 'N/A')}")
            print(f"📈 Total interactions: {data.get('analysis', {}).get('total_interactions', 0)}")
            print(f"🔄 Is real-time: {data.get('analysis', {}).get('is_real_time', False)}")
            print(f"📍 Data source: {data.get('analysis', {}).get('data_source', 'unknown')}")
            
            # Show first 3 products
            print(f"\n🛍️ Top 3 RECOMMENDATIONS:")
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"   {i}. {rec.get('name', 'Unknown')} - {rec.get('category', 'Unknown')}")
                print(f"      💡 {rec.get('reason', 'No reason')}")
            
            initial_main_category = data.get('analysis', {}).get('main_category')
            initial_total_interactions = data.get('analysis', {}).get('total_interactions', 0)
            
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return
    
    print(f"\n⏱️ Waiting 3 seconds before second test...")
    time.sleep(3)
    
    # Test 2: Kiểm tra lại sau vài giây
    print(f"\n--- TEST 2: Check for Real-time Changes ---")
    
    try:
        response = requests.get(f'http://localhost:5002/recommendations/{user_id}', 
                              params={'num_recs': 10})
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 Total recommendations: {data.get('total', 0)}")
            print(f"🗂️ Main category: {data.get('analysis', {}).get('main_category', 'N/A')}")
            print(f"📈 Total interactions: {data.get('analysis', {}).get('total_interactions', 0)}")
            print(f"🔄 Is real-time: {data.get('analysis', {}).get('is_real_time', False)}")
            print(f"📍 Data source: {data.get('analysis', {}).get('data_source', 'unknown')}")
            
            # Check for changes
            current_main_category = data.get('analysis', {}).get('main_category')
            current_total_interactions = data.get('analysis', {}).get('total_interactions', 0)
            
            print(f"\n🔍 COMPARISON:")
            print(f"   Main category: {initial_main_category} → {current_main_category}")
            print(f"   Total interactions: {initial_total_interactions} → {current_total_interactions}")
            
            if current_total_interactions > initial_total_interactions:
                print(f"   ✅ NEW INTERACTIONS DETECTED! (+{current_total_interactions - initial_total_interactions})")
            elif data.get('analysis', {}).get('is_real_time'):
                print(f"   🔄 REAL-TIME MODE ACTIVE")
            else:
                print(f"   ⚠️ No new interactions")
            
            # Show updated products
            print(f"\n🛍️ Updated Top 3 RECOMMENDATIONS:")
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"   {i}. {rec.get('name', 'Unknown')} - {rec.get('category', 'Unknown')}")
                print(f"      💡 {rec.get('reason', 'No reason')}")
                
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Kiểm tra analysis chi tiết
    print(f"\n--- TEST 3: Detailed Analysis ---")
    
    try:
        response = requests.get(f'http://localhost:5002/analyze/{user_id}')
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 BEHAVIOR ANALYSIS:")
            analysis = data.get('analysis', {})
            
            if 'clicked_categories' in analysis:
                print(f"   🖱️ Clicked categories: {analysis['clicked_categories']}")
            if 'viewed_categories' in analysis:
                print(f"   👀 Viewed categories: {analysis['viewed_categories']}")
            if 'total_interactions' in analysis:
                print(f"   📈 Total interactions: {analysis['total_interactions']}")
                
        else:
            print(f"❌ Analysis Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Analysis Exception: {e}")
    
    print(f"\n{'🎯'*20}")
    print("✅ REAL-TIME TEST COMPLETED!")
    print("💡 Tips:")
    print("   - Click vào sản phẩm trên website")
    print("   - Chạy lại script này để thấy changes")
    print("   - Kiểm tra 'is_real_time': true trong response")
    print(f"{'🎯'*20}")

if __name__ == "__main__":
    test_real_time_updates()