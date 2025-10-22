import sqlite3
import os
import json
from datetime import datetime

def database_overview():
    db_path = os.path.join('web-app', 'instance', 'ecommerce.db')
    
    if not os.path.exists(db_path):
        print("❌ Database không tồn tại tại:", db_path)
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🗄️  BIG DATA E-COMMERCE DATABASE OVERVIEW")
    print("="*60)
    
    # 1. Users
    print("\n👥 USERS:")
    cursor.execute("SELECT COUNT(*) FROM user")
    user_count = cursor.fetchone()[0]
    print(f"Tổng số users: {user_count}")
    
    cursor.execute("SELECT id, username, email FROM user ORDER BY id")
    users = cursor.fetchall()
    for user in users:
        print(f"  ID {user[0]}: {user[1]} ({user[2]})")
    
    # 2. Products by Category
    print(f"\n📦 PRODUCTS BY CATEGORY:")
    cursor.execute("SELECT COUNT(*) FROM product")
    product_count = cursor.fetchone()[0]
    print(f"Tổng số products: {product_count}")
    
    cursor.execute("SELECT category, COUNT(*) FROM product GROUP BY category ORDER BY COUNT(*) DESC")
    categories = cursor.fetchall()
    for cat in categories:
        print(f"  📂 {cat[0]}: {cat[1]} sản phẩm")
    
    # 3. User Interactions Summary
    print(f"\n📊 USER INTERACTIONS SUMMARY:")
    cursor.execute("SELECT COUNT(*) FROM user_interaction")
    interaction_count = cursor.fetchone()[0]
    print(f"Tổng số interactions: {interaction_count}")
    
    if interaction_count > 0:
        cursor.execute("""
            SELECT u.username, ui.interaction_type, COUNT(*) as count
            FROM user_interaction ui
            JOIN user u ON ui.user_id = u.id
            GROUP BY u.username, ui.interaction_type
            ORDER BY u.username, count DESC
        """)
        interactions = cursor.fetchall()
        
        print("\n📈 Chi tiết interactions theo user:")
        current_user = None
        for interaction in interactions:
            if current_user != interaction[0]:
                current_user = interaction[0]
                print(f"\n  👤 {current_user}:")
            print(f"    🔸 {interaction[1]}: {interaction[2]} lần")
    else:
        print("  ⚠️  Chưa có interactions nào!")
    
    # 4. Recent Activities
    print(f"\n🕒 RECENT ACTIVITIES (10 gần nhất):")
    cursor.execute("""
        SELECT u.username, ui.interaction_type, ui.details, ui.timestamp
        FROM user_interaction ui
        JOIN user u ON ui.user_id = u.id
        ORDER BY ui.timestamp DESC
        LIMIT 10
    """)
    recent_activities = cursor.fetchall()
    
    if recent_activities:
        for activity in recent_activities:
            details = json.loads(activity[2]) if activity[2] else {}
            timestamp = activity[3]
            product_name = details.get('product_name', details.get('query', 'N/A'))
            print(f"  🔹 {timestamp} | {activity[0]} | {activity[1]} | {product_name}")
    else:
        print("  ⚠️  Chưa có activities nào!")
    
    # 5. Recommendations Data Check
    print(f"\n🤖 KAFKA DATA FOR RECOMMENDATIONS:")
    cursor.execute("""
        SELECT u.username, 
               SUM(CASE WHEN ui.interaction_type = 'click' THEN 1 ELSE 0 END) as clicks,
               SUM(CASE WHEN ui.interaction_type = 'view' THEN 1 ELSE 0 END) as views,
               SUM(CASE WHEN ui.interaction_type = 'search' THEN 1 ELSE 0 END) as searches
        FROM user u
        LEFT JOIN user_interaction ui ON u.id = ui.user_id
        GROUP BY u.id, u.username
        ORDER BY (clicks + views + searches) DESC
    """)
    user_stats = cursor.fetchall()
    
    for stat in user_stats:
        total = (stat[1] or 0) + (stat[2] or 0) + (stat[3] or 0)
        if total > 0:
            print(f"  👤 {stat[0]}: {stat[1]} clicks, {stat[2]} views, {stat[3]} searches (Total: {total})")
        else:
            print(f"  👤 {stat[0]}: Chưa có hoạt động")
    
    conn.close()
    print(f"\n✅ Database check completed!")

def check_specific_user(user_id):
    db_path = os.path.join('web-app', 'instance', 'ecommerce.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # User info
    cursor.execute("SELECT username, email FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ User ID {user_id} không tồn tại!")
        conn.close()
        return
    
    print(f"\n🔍 CHI TIẾT USER ID {user_id}: {user[0]}")
    print("="*50)
    
    # All interactions
    cursor.execute("""
        SELECT interaction_type, details, timestamp 
        FROM user_interaction 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    """, (user_id,))
    interactions = cursor.fetchall()
    
    if interactions:
        print(f"📊 Tổng {len(interactions)} interactions:")
        for i, interaction in enumerate(interactions, 1):
            details = json.loads(interaction[1]) if interaction[1] else {}
            timestamp = interaction[2]
            interaction_type = interaction[0]
            
            product_info = ""
            if 'product_name' in details:
                product_info = f"Product: {details['product_name']}"
            elif 'query' in details:
                product_info = f"Search: {details['query']}"
            elif 'category' in details:
                product_info = f"Category: {details['category']}"
            
            print(f"  {i:2d}. {timestamp} | {interaction_type:10} | {product_info}")
    else:
        print("⚠️  User này chưa có interactions nào!")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 STARTING DATABASE CHECK...")
    database_overview()
    
    print("\n" + "="*60)
    print("💡 Để check user cụ thể, chạy:")
    print("   python check_database.py USER_ID")
    print("   Ví dụ: python -c \"from check_database import check_specific_user; check_specific_user(1)\"")