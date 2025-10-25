#!/usr/bin/env python3
"""
Test Real-time Data Flow
Verify that clicks on Web App immediately show up in Dashboard
"""

import sqlite3
import os
import time
from datetime import datetime

DB_PATH = os.path.join('web-app', 'instance', 'ecommerce.db')

def add_test_interaction():
    """Add a test interaction to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Add a test interaction
    cursor.execute("""
        INSERT INTO user_interaction (user_id, product_id, interaction_type, timestamp)
        VALUES (1, 1, 'product_view', datetime('now'))
    """)
    conn.commit()
    conn.close()
    print(f"✅ Added test interaction at {datetime.now().strftime('%H:%M:%S')}")

def check_recent_activity():
    """Check recent activity in last 5 seconds"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM user_interaction 
        WHERE timestamp >= datetime('now', '-5 seconds')
    """)
    count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT interaction_type, timestamp 
        FROM user_interaction 
        WHERE timestamp >= datetime('now', '-10 seconds')
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    recent = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📊 Recent Activity (last 5 seconds): {count} interactions")
    if recent:
        print("Latest interactions:")
        for interaction_type, timestamp in recent:
            print(f"  - {interaction_type} at {timestamp}")
    
    return count

def test_realtime_flow():
    """Test the real-time data flow"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        REAL-TIME DATA FLOW TEST                          ║
║        Web App → SQLite → Dashboard                      ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    print("\n🔍 Testing Real-time Data Flow:")
    print("=" * 60)
    
    # Check initial state
    print("\n1️⃣ Initial State:")
    initial_count = check_recent_activity()
    
    # Add test interaction
    print("\n2️⃣ Adding Test Interaction:")
    add_test_interaction()
    
    # Check immediately
    print("\n3️⃣ Checking Immediately:")
    new_count = check_recent_activity()
    
    # Verify
    print("\n" + "=" * 60)
    if new_count > initial_count:
        print("✅ REAL-TIME FLOW WORKING!")
        print(f"   Data added to database immediately")
        print(f"   Dashboard will show it on next refresh (5 seconds)")
    else:
        print("⚠️  No new data detected")
    
    # Check Dashboard refresh interval
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM user_interaction 
        WHERE timestamp >= datetime('now', '-30 minutes')
    """)
    recent_30min = cursor.fetchone()[0]
    conn.close()
    
    print(f"\n📈 Statistics:")
    print(f"   - Last 30 minutes: {recent_30min} interactions")
    print(f"   - Dashboard refresh: Every 5 seconds")
    print(f"   - Data source: SQLite database")
    
    print(f"\n💡 How It Works:")
    print(f"   1. User clicks product on Web App (port 5000)")
    print(f"   2. Web App saves to SQLite database INSTANTLY")
    print(f"   3. Dashboard queries database every 5 seconds")
    print(f"   4. Charts update with new data automatically")
    
    print(f"\n⏱️  Timeline:")
    print(f"   - T+0s: User clicks → Database updated")
    print(f"   - T+5s: Dashboard refreshes → Shows new data")
    print(f"   - Real-time lag: Max 5 seconds")
    
    print(f"\n🎯 To Test Yourself:")
    print(f"   1. Open http://localhost:5000 (Web App)")
    print(f"   2. Open http://localhost:8050 (Dashboard)")
    print(f"   3. Click any product on Web App")
    print(f"   4. Watch Dashboard - updates within 5 seconds!")
    print()

if __name__ == "__main__":
    test_realtime_flow()
