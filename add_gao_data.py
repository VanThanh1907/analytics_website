import sqlite3
from datetime import datetime

# Kết nối với database
db_path = 'web-app/instance/ecommerce.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Kiểm tra cấu trúc bảng user_interaction
cursor.execute("PRAGMA table_info(user_interaction);")
columns = cursor.fetchall()
print('Cấu trúc bảng user_interaction:')
for col in columns:
    print(f'- {col[1]} ({col[2]})')

# Thêm nhiều interactions về gạo cho user ID 3 (user hiện tại)
interactions = [
    (3, 'product_view', 1, 'Gạo tẻ Long An'),  # Gạo tẻ
    (3, 'product_view', 2, 'Gạo thơm Jasmine'),  # Gạo thơm  
    (3, 'search', None, 'gạo'),
    (3, 'search', None, 'gạo tẻ'),
    (3, 'category_view', None, 'Thực phẩm tươi sống'),
    (3, 'product_view', 3, 'Gạo nàng hương'),
    (3, 'product_view', 4, 'Gạo ST25'),
    (3, 'search', None, 'gạo jasmine'),
    (3, 'product_click', 1, 'Clicked gạo tẻ'),
    (3, 'product_click', 2, 'Clicked gạo thơm'),
]

# Thêm từng interaction
current_time = datetime.now().isoformat()
for user_id, interaction_type, product_id, details in interactions:
    cursor.execute('''
        INSERT INTO user_interaction (user_id, interaction_type, product_id, details, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, interaction_type, product_id, details, current_time))

conn.commit()

# Kiểm tra dữ liệu đã thêm
cursor.execute("SELECT user_id, interaction_type, product_id, details FROM user_interaction WHERE user_id = 3;")
data = cursor.fetchall()
print(f'\nDữ liệu cho user 3 ({len(data)} records):')
for row in data:
    print(f'- User {row[0]}: {row[1]} - Product {row[2]} - {row[3]}')

conn.close()
print('\n✅ Đã thêm test interactions về gạo cho user ID 3')