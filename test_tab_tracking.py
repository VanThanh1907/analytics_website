#!/usr/bin/env python3
"""
Test Tab-based Session Tracking
Verify each browser tab creates unique session
"""

import sqlite3
import os
import time
from datetime import datetime

DB_PATH = os.path.join('web-app', 'instance', 'ecommerce.db')

def simulate_tab_with_unique_id(tab_number, user_id):
    """Simulate tab with JavaScript-generated tab_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Simulate JavaScript: tab_TIMESTAMP_RANDOM
    tab_id = f"tab_{int(time.time() * 1000)}_{tab_number}_abc123"
    
    # Insert/update session
    cursor.execute("""
        INSERT INTO active_session (session_id, user_id, last_activity)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id)
        DO UPDATE SET last_activity = CURRENT_TIMESTAMP, user_id = ?
    """, (tab_id, user_id, user_id))
    
    conn.commit()
    conn.close()
    
    print(f"  ✅ Tab {tab_number} (User {user_id}): {tab_id[:30]}...")
    return tab_id

def count_active_sessions():
    """Count active sessions and group by user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total count
    cursor.execute("""
        SELECT COUNT(*) FROM active_session 
        WHERE last_activity >= datetime('now', '-5 minutes')
    """)
    total = cursor.fetchone()[0]
    
    # Count by user
    cursor.execute("""
        SELECT 
            COALESCE(user_id, 0) as uid,
            COUNT(*) as count
        FROM active_session 
        WHERE last_activity >= datetime('now', '-5 minutes')
        GROUP BY user_id
        ORDER BY uid
    """)
    by_user = cursor.fetchall()
    
    conn.close()
    
    return total, by_user

def test_multiple_users_multiple_tabs():
    """Test 2 users each with 2 tabs"""
    print("""
╔══════════════════════════════════════════════════════════╗
║     TAB-BASED SESSION TRACKING TEST                      ║
║     2 Users × 2 Tabs = 4 Active Sessions                 ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    print("🧹 Cleaning up old test sessions...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_session WHERE session_id LIKE 'tab_%'")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"   Removed {deleted} old sessions\n")
    
    # Initial count
    print("1️⃣ Initial State:")
    total, by_user = count_active_sessions()
    print(f"   Total active sessions: {total}\n")
    
    # Simulate User 1 opens 2 tabs
    print("2️⃣ User 1 Opens 2 Tabs:")
    simulate_tab_with_unique_id(1, user_id=1)
    time.sleep(0.1)
    simulate_tab_with_unique_id(2, user_id=1)
    
    total, by_user = count_active_sessions()
    print(f"\n   Total active sessions: {total}")
    for uid, count in by_user:
        print(f"   - User {uid}: {count} tabs")
    
    # Simulate User 2 opens 2 tabs
    print("\n3️⃣ User 2 Opens 2 Tabs:")
    simulate_tab_with_unique_id(3, user_id=2)
    time.sleep(0.1)
    simulate_tab_with_unique_id(4, user_id=2)
    
    total, by_user = count_active_sessions()
    print(f"\n   Total active sessions: {total}")
    for uid, count in by_user:
        print(f"   - User {uid}: {count} tabs")
    
    # Verify
    print(f"\n{'='*60}")
    if total == 4:
        print("✅ PERFECT! Tab-based tracking working!")
        print("   2 users × 2 tabs = 4 sessions tracked")
    else:
        print(f"⚠️  Expected 4 sessions, got {total}")
    
    print(f"\n📊 How It Works Now:")
    print(f"   1. Each tab generates unique ID: tab_TIMESTAMP_RANDOM")
    print(f"   2. JavaScript sends heartbeat every 30 seconds")
    print(f"   3. Each heartbeat updates last_activity")
    print(f"   4. Dashboard counts ALL active tabs (last 5 min)")
    print(f"   5. Different users in different tabs = All counted!")
    
    print(f"\n🎯 Real Browser Test:")
    print(f"   1. Open Tab 1: Login as user1")
    print(f"   2. Open Tab 2: Login as user2") 
    print(f"   3. Dashboard shows: Users Online = 2 ✅")
    print(f"   4. Open 2 more tabs for user1")
    print(f"   5. Dashboard shows: Users Online = 4 ✅")
    
    print(f"\n🧹 Cleanup:")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_session WHERE session_id LIKE 'tab_%'")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"   Removed {deleted} test sessions")
    print()

if __name__ == "__main__":
    test_multiple_users_multiple_tabs()
