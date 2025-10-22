import sqlite3

# Kết nối với database
db_path = 'web-app/instance/ecommerce.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Lấy danh sách tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print('Tables trong database:')
for table in tables:
    print(f'- {table[0]}')

# Kiểm tra cấu trúc bảng UserInteraction
try:
    cursor.execute("PRAGMA table_info(UserInteraction);")
    columns = cursor.fetchall()
    print('\nCấu trúc bảng UserInteraction:')
    for col in columns:
        print(f'- {col[1]} ({col[2]})')
        
    # Kiểm tra dữ liệu hiện có
    cursor.execute("SELECT user_id, action, product_id, details FROM UserInteraction LIMIT 10;")
    data = cursor.fetchall()
    print(f'\nDữ liệu hiện có ({len(data)} records):')
    for row in data:
        print(f'- User {row[0]}: {row[1]} - {row[2]} - {row[3]}')
        
except Exception as e:
    print(f'Lỗi khi truy cập UserInteraction: {e}')

conn.close()