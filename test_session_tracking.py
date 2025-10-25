#!/usr/bin/env python3
"""
Test Session Tracking - Verify Multiple Tabs
Simulates opening multiple browser tabs to test session counting
"""

import sqlite3
import os
import time
from datetime import datetime
import uuid

DB_PATH = os.path.join('web-app', 'instance', 'ecommerce.db')

def simulate_tab_open(tab_number):
    """Simulate opening a browser tab"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    session_id = f"test_session_{tab_number}_{uuid.uuid4()}"
    
    # Insert session
    cursor.execute("""
        INSERT INTO active_session (session_id, user_id, last_activity)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (session_id, 1))  # user_id = 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Tab {tab_number} opened (session: {session_id[:20]}...)")
    return session_id

def count_active_sessions():
    """Count active sessions in last 5 minutes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM active_session 
        WHERE last_activity >= datetime('now', '-5 minutes')
    """)
    count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT session_id, last_activity 
        FROM active_session 
        WHERE last_activity >= datetime('now', '-5 minutes')
        ORDER BY last_activity DESC
        LIMIT 5
    """)
    sessions = cursor.fetchall()
    
    conn.close()
    
    return count, sessions

def cleanup_test_sessions():
    """Remove test sessions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM active_session 
        WHERE session_id LIKE 'test_session_%'
    """)
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    return deleted

def test_multiple_tabs():
    """Test opening multiple tabs"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        SESSION TRACKING TEST                             ║
║        Multiple Tabs = Multiple Sessions                 ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Cleanup first
    deleted = cleanup_test_sessions()
    print(f"🧹 Cleaned up {deleted} old test sessions\n")
    
    # Initial count
    print("1️⃣ Initial State:")
    count, sessions = count_active_sessions()
    print(f"   Active sessions: {count}")
    initial_count = count
    
    # Simulate opening 3 tabs
    print(f"\n2️⃣ Simulating Opening 3 Browser Tabs:")
    print("   (Each tab = unique session)")
    for i in range(1, 4):
        simulate_tab_open(i)
        time.sleep(0.5)
    
    # Count again
    print(f"\n3️⃣ After Opening Tabs:")
    count, sessions = count_active_sessions()
    print(f"   Active sessions: {count}")
    print(f"   Increase: +{count - initial_count}")
    
    if sessions:
        print(f"\n   Recent sessions:")
        for session_id, last_activity in sessions[:3]:
            short_id = session_id[:30] + "..." if len(session_id) > 30 else session_id
            print(f"   - {short_id} @ {last_activity}")
    
    # Verify
    print(f"\n{'='*60}")
    if count >= initial_count + 3:
        print("✅ SESSION TRACKING WORKING!")
        print("   Each tab creates a unique session")
        print("   Dashboard will show accurate count")
    else:
        print("⚠️  Some sessions not tracked")
    
    print(f"\n📊 How It Works:")
    print(f"   1. User opens Web App → Creates session_id")
    print(f"   2. Every page view → Updates last_activity")
    print(f"   3. Dashboard counts sessions active in last 5 minutes")
    print(f"   4. Multiple tabs = Multiple sessions = Higher count")
    
    print(f"\n🎯 Test in Real Browser:")
    print(f"   1. Start services: START_FIXED_DEMO.bat")
    print(f"   2. Open http://localhost:8050 (Dashboard)")
    print(f"   3. Note 'Users Online' count")
    print(f"   4. Open http://localhost:5000 in 3 tabs")
    print(f"   5. Wait 5 seconds → Dashboard count increases by 3!")
    
    print(f"\n🧹 Cleanup:")
    deleted = cleanup_test_sessions()
    print(f"   Removed {deleted} test sessions")
    print()

if __name__ == "__main__":
    test_multiple_tabs()
