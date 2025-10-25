#!/usr/bin/env python3
"""
Add Session Tracking to Database
Track active browser sessions for real-time user count
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join('web-app', 'instance', 'ecommerce.db')

def add_session_table():
    """Add session tracking table to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create session table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            user_id INTEGER,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_last_activity 
        ON active_session(last_activity)
    """)
    
    conn.commit()
    
    print("✅ Session table created successfully!")
    print("   - Table: active_session")
    print("   - Columns: session_id, user_id, last_activity")
    print("   - Index: idx_session_last_activity")
    
    # Check current sessions
    cursor.execute("SELECT COUNT(*) FROM active_session")
    count = cursor.fetchone()[0]
    print(f"   - Current sessions: {count}")
    
    conn.close()

def cleanup_old_sessions():
    """Remove sessions older than 5 minutes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM active_session 
        WHERE last_activity < datetime('now', '-5 minutes')
    """)
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Cleaned up {deleted} old sessions")

if __name__ == "__main__":
    print("🔧 Setting up session tracking...")
    add_session_table()
    cleanup_old_sessions()
    print("\n✅ Session tracking is ready!")
    print("\n💡 Next steps:")
    print("   1. Web App will track sessions automatically")
    print("   2. Dashboard will show accurate 'Users Online' count")
    print("   3. Each browser tab = 1 session")
