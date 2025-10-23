"""
DEBUG: Kiểm tra dữ liệu interactions trong database
"""
import sqlite3
import os
from datetime import datetime

# Path to database
db_path = os.path.join(os.path.dirname(__file__), 'web-app', 'instance', 'ecommerce.db')

print(f"📂 Database path: {db_path}")
print(f"✅ Database exists: {os.path.exists(db_path)}")
print()

if not os.path.exists(db_path):
    print("❌ Database không tồn tại!")
    print("Hãy chạy web app trước để tạo database:")
    print("  cd web-app")
    print("  python app.py")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check tables
print("=" * 60)
print("📊 TABLES IN DATABASE")
print("=" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"  ✅ {table[0]}")
print()

# Check users
print("=" * 60)
print("👥 USERS")
print("=" * 60)
cursor.execute("SELECT id, username, email FROM user LIMIT 10")
users = cursor.fetchall()
if users:
    for user in users:
        print(f"  User ID {user[0]}: {user[1]} ({user[2]})")
else:
    print("  ⚠️ Chưa có users")
print()

# Check products count
print("=" * 60)
print("📦 PRODUCTS")
print("=" * 60)
cursor.execute("SELECT COUNT(*) FROM product")
product_count = cursor.fetchone()[0]
print(f"  Total products: {product_count}")

cursor.execute("SELECT DISTINCT category FROM product")
categories = cursor.fetchall()
print(f"  Categories ({len(categories)}):")
for cat in categories:
    print(f"    - {cat[0]}")
print()

# Check interactions
print("=" * 60)
print("🔍 USER INTERACTIONS")
print("=" * 60)
cursor.execute("SELECT COUNT(*) FROM user_interaction")
interaction_count = cursor.fetchone()[0]
print(f"  Total interactions: {interaction_count}")
print()

if interaction_count > 0:
    # Show recent interactions
    print("  📝 Recent interactions (last 20):")
    query = """
        SELECT ui.id, ui.user_id, u.username, ui.product_id, p.name, 
               ui.interaction_type, ui.timestamp, p.category
        FROM user_interaction ui
        LEFT JOIN user u ON ui.user_id = u.id
        LEFT JOIN product p ON ui.product_id = p.id
        ORDER BY ui.timestamp DESC
        LIMIT 20
    """
    cursor.execute(query)
    interactions = cursor.fetchall()
    
    for interaction in interactions:
        int_id, user_id, username, prod_id, prod_name, int_type, timestamp, category = interaction
        print(f"    [{timestamp}] User: {username or user_id} → {int_type.upper()}")
        print(f"       Product: {prod_name or prod_id} ({category})")
        print()
    
    # Count by interaction type
    print("  📊 Interactions by type:")
    cursor.execute("""
        SELECT interaction_type, COUNT(*) 
        FROM user_interaction 
        GROUP BY interaction_type
    """)
    type_counts = cursor.fetchall()
    for int_type, count in type_counts:
        print(f"    {int_type}: {count}")
    print()
    
    # Count by user
    print("  👤 Interactions by user:")
    cursor.execute("""
        SELECT u.username, u.id, COUNT(*) 
        FROM user_interaction ui
        LEFT JOIN user u ON ui.user_id = u.id
        GROUP BY ui.user_id
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    user_counts = cursor.fetchall()
    for username, user_id, count in user_counts:
        print(f"    {username or user_id}: {count} interactions")
    
else:
    print("  ⚠️ CHƯA CÓ INTERACTIONS NÀO!")
    print()
    print("  💡 Để tạo interactions:")
    print("     1. Đảm bảo web app đang chạy")
    print("     2. Login vào hệ thống")
    print("     3. Click vào các sản phẩm")
    print("     4. Chạy lại script này để kiểm tra")

conn.close()

print()
print("=" * 60)
print("✅ CHECK COMPLETED")
print("=" * 60)
