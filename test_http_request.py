#!/usr/bin/env python3
"""
Direct Web App Test via HTTP Request
Test what happens when we call the recommendations route
"""

import requests
import sys

def test_recommendations_route():
    """Test the recommendations route directly"""
    
    print("🌐 TESTING WEB APP RECOMMENDATIONS ROUTE VIA HTTP")
    print("=" * 60)
    
    # First, we need to be logged in
    # Let's try to access the recommendations page without login first
    
    try:
        print("🔍 Testing recommendations route...")
        
        # Try to access recommendations (should redirect to login)
        url = "http://localhost:5000/recommendations"
        response = requests.get(url)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 URL after redirects: {response.url}")
        
        if response.status_code == 200:
            print("✅ Successfully accessed recommendations")
            # Check if we can find priority-related content in the HTML
            html_content = response.text
            
            if "same_category" in html_content:
                print("✅ Found 'same_category' in response")
            if "related_category" in html_content:
                print("✅ Found 'related_category' in response")
            if "8 sản phẩm cùng danh mục" in html_content:
                print("✅ Found category-based headers in response")
            if "Gạo ST25" in html_content:
                print("✅ Found latest click product reference")
                
            # Save response to file for debugging
            with open("debug_recommendations_response.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("💾 Saved response to debug_recommendations_response.html")
            
        else:
            print(f"❌ Got status {response.status_code}, likely redirect to login")
            print(f"📍 Response URL: {response.url}")
            
        # Try demo route (no login required)
        print("\n🎭 Testing demo recommendations route...")
        demo_url = "http://localhost:5000/demo-recommendations"
        demo_response = requests.get(demo_url)
        
        print(f"📊 Demo Status Code: {demo_response.status_code}")
        
        if demo_response.status_code == 200:
            print("✅ Successfully accessed demo recommendations")
            demo_html = demo_response.text
            
            # Save demo response to file for debugging
            with open("debug_demo_recommendations_response.html", "w", encoding="utf-8") as f:
                f.write(demo_html)
            print("💾 Saved demo response to debug_demo_recommendations_response.html")
            
            # Check for priority content in demo
            if "same_category" in demo_html:
                print("✅ Found 'same_category' in demo response")
            if "related_category" in demo_html:
                print("✅ Found 'related_category' in demo response")
            if "8 sản phẩm cùng danh mục" in demo_html:
                print("✅ Found category-based headers in demo response")
                
        print("\n💡 Check the saved HTML files to see actual template output!")
        
    except Exception as e:
        print(f"❌ Error testing web app: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_recommendations_route()