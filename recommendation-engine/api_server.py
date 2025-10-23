from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
import os
import random
from datetime import datetime

# Import simplified recommendation engine
try:
    from recommendation_api import RecommendationAPI
    HAS_FULL_ENGINE = True
except ImportError:
    HAS_FULL_ENGINE = False
    print("⚠️ Warning: Full recommendation engine not available, using mock version")

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Real-time recommendation engine using SQLite
class RealDataRecommendationEngine:
    def __init__(self):
        # Connect to SQLite database to read real interactions
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'web-app', 'instance', 'ecommerce.db'))
        
        # Lưu trữ lịch sử gợi ý của từng user
        self.user_recommendation_history = {}
        
        # ✅ KHÔNG CÒN MOCK DATA - CHỈ DÙNG DATABASE THẬT
        logger.info(f"✅ Real Data Recommendation Engine initialized with SQLite: {self.db_path}")
            # Thực phẩm tươi sống (8 sản phẩm)
            {'id': 1, 'name': 'Gạo ST25 túi 5kg', 'category': 'Thực phẩm tươi sống', 'price': 180000},
            {'id': 2, 'name': 'Gạo tẻ thường 5kg', 'category': 'Thực phẩm tươi sống', 'price': 120000},
            {'id': 3, 'name': 'Gạo nàng hương 2kg', 'category': 'Thực phẩm tươi sống', 'price': 85000},
            {'id': 4, 'name': 'Gà công nghiệp 1.2kg', 'category': 'Thực phẩm tươi sống', 'price': 85000},
            {'id': 5, 'name': 'Thịt heo ba chỉ 500g', 'category': 'Thực phẩm tươi sống', 'price': 95000},
            {'id': 6, 'name': 'Cá tra phi lê 400g', 'category': 'Thực phẩm tươi sống', 'price': 75000},
            {'id': 7, 'name': 'Tôm sú tươi 300g', 'category': 'Thực phẩm tươi sống', 'price': 120000},
            {'id': 8, 'name': 'Trứng gà tươi 10 quả', 'category': 'Thực phẩm tươi sống', 'price': 35000},
            
            # Đồ uống & Nước giải khát (6 sản phẩm)
            {'id': 15, 'name': 'Coca Cola lon 330ml', 'category': 'Đồ uống & Nước giải khát', 'price': 15000},
            {'id': 16, 'name': 'Pepsi lon 330ml', 'category': 'Đồ uống & Nước giải khát', 'price': 15000},
            {'id': 17, 'name': 'Nước cam Tropicana 1L', 'category': 'Đồ uống & Nước giải khát', 'price': 35000},
            {'id': 18, 'name': 'Trà xanh C2 500ml', 'category': 'Đồ uống & Nước giải khát', 'price': 12000},
            {'id': 19, 'name': 'Nước lọc Aquafina 500ml', 'category': 'Đồ uống & Nước giải khát', 'price': 8000},
            {'id': 20, 'name': 'Cà phê sữa đá G7 hộp', 'category': 'Đồ uống & Nước giải khát', 'price': 45000},
            
            # Trái cây tươi (5 sản phẩm)
            {'id': 28, 'name': 'Cam tươi Việt Nam 1kg', 'category': 'Trái cây tươi', 'price': 45000},
            {'id': 29, 'name': 'Táo Fuji Nhật Bản 1kg', 'category': 'Trái cây tươi', 'price': 85000},
            {'id': 30, 'name': 'Chuối tiêu Đắk Lắk 1kg', 'category': 'Trái cây tươi', 'price': 25000},
            {'id': 31, 'name': 'Xoài cát Hòa Lộc 1kg', 'category': 'Trái cây tươi', 'price': 65000},
            {'id': 32, 'name': 'Nho đen không hạt 500g', 'category': 'Trái cây tươi', 'price': 95000},
            
            # Rau củ quả (5 sản phẩm)
            {'id': 35, 'name': 'Cải thảo 1kg', 'category': 'Rau củ quả', 'price': 18000},
            {'id': 36, 'name': 'Cà rót tím 500g', 'category': 'Rau củ quả', 'price': 22000},
            {'id': 37, 'name': 'Củ cải trắng 1kg', 'category': 'Rau củ quả', 'price': 20000},
            {'id': 38, 'name': 'Bí đỏ Đà Lạt 1kg', 'category': 'Rau củ quả', 'price': 35000},
            {'id': 39, 'name': 'Rau muống 300g', 'category': 'Rau củ quả', 'price': 8000},
            
            # Thực phẩm khô & Gia vị (8 sản phẩm)
            {'id': 42, 'name': 'Hạt điều rang muối 200g', 'category': 'Thực phẩm khô & Gia vị', 'price': 85000},
            {'id': 43, 'name': 'Nước mắm Phú Quốc 500ml', 'category': 'Thực phẩm khô & Gia vị', 'price': 45000},
            {'id': 44, 'name': 'Đường cát trắng 1kg', 'category': 'Thực phẩm khô & Gia vị', 'price': 25000},
            {'id': 45, 'name': 'Muối tinh I-ốt 1kg', 'category': 'Thực phẩm khô & Gia vị', 'price': 15000},
            {'id': 46, 'name': 'Mì ăn liền Hảo Hảo gói', 'category': 'Thực phẩm khô & Gia vị', 'price': 4500},
            {'id': 47, 'name': 'Nước tương đậu nành 500ml', 'category': 'Thực phẩm khô & Gia vị', 'price': 35000},
            {'id': 48, 'name': 'Hạt nêm Knorr 400g', 'category': 'Thực phẩm khô & Gia vị', 'price': 28000},
            {'id': 49, 'name': 'Dầu ăn Neptune 1L', 'category': 'Thực phẩm khô & Gia vị', 'price': 55000},
            
            # Bánh kẹo & Snacks (4 sản phẩm)
            {'id': 58, 'name': 'Bánh quy chocolate 300g', 'category': 'Bánh kẹo & Snacks', 'price': 55000},
            {'id': 59, 'name': 'Kẹo dẻo Haribo 100g', 'category': 'Bánh kẹo & Snacks', 'price': 35000},
            {'id': 60, 'name': 'Snack khoai tây Pringles', 'category': 'Bánh kẹo & Snacks', 'price': 65000},
            {'id': 61, 'name': 'Bánh mì sandwich 200g', 'category': 'Bánh kẹo & Snacks', 'price': 45000},
            
            # Sản phẩm làm đẹp & Chăm sóc cá nhân (8 sản phẩm)
            {'id': 70, 'name': 'Kem dưỡng da Olay 50ml', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 150000},
            {'id': 71, 'name': 'Sữa rửa mặt Neutrogena 200ml', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 180000},
            {'id': 72, 'name': 'Dầu gội Head & Shoulders 400ml', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 95000},
            {'id': 73, 'name': 'Sữa tắm Dove 500ml', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 85000},
            {'id': 74, 'name': 'Kem chống nắng Sunplay 50ml', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 120000},
            {'id': 75, 'name': 'Serum vitamin C 30ml', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 250000},
            {'id': 76, 'name': 'Nước hoa hồng Mamonde 200ml', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 190000},
            {'id': 77, 'name': 'Son môi MAC Rouge 3.5g', 'category': 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'price': 320000},
            
            # Đồ gia dụng nhà bếp (6 sản phẩm)
            {'id': 80, 'name': 'Chảo chống dính 24cm', 'category': 'Đồ gia dụng nhà bếp', 'price': 250000},
            {'id': 81, 'name': 'Nồi cơm điện 1.2L', 'category': 'Đồ gia dụng nhà bếp', 'price': 450000},
            {'id': 82, 'name': 'Bộ dao nhà bếp 5 món', 'category': 'Đồ gia dụng nhà bếp', 'price': 180000},
            {'id': 83, 'name': 'Máy xay sinh tố 1.5L', 'category': 'Đồ gia dụng nhà bếp', 'price': 350000},
            {'id': 84, 'name': 'Bình đun siêu tốc 1.7L', 'category': 'Đồ gia dụng nhà bếp', 'price': 280000},
            {'id': 85, 'name': 'Bộ chén đĩa gốm sứ', 'category': 'Đồ gia dụng nhà bếp', 'price': 220000}
        ]
        
        self.category_relations = {
            'Thực phẩm tươi sống': ['Rau củ quả', 'Thực phẩm khô & Gia vị'],
            'Đồ uống & Nước giải khát': ['Bánh kẹo & Snacks', 'Trái cây tươi'],
            'Trái cây tươi': ['Đồ uống & Nước giải khát', 'Rau củ quả'],
            'Rau củ quả': ['Thực phẩm tươi sống', 'Trái cây tươi'],
            'Thực phẩm khô & Gia vị': ['Thực phẩm tươi sống', 'Đồ gia dụng nhà bếp'],
            'Bánh kẹo & Snacks': ['Đồ uống & Nước giải khát', 'Trái cây tươi'],
            'Sản phẩm làm đẹp & Chăm sóc cá nhân': ['Đồ gia dụng nhà bếp', 'Bánh kẹo & Snacks'],
            'Đồ gia dụng nhà bếp': ['Thực phẩm khô & Gia vị', 'Sản phẩm làm đẹp & Chăm sóc cá nhân']
        }
        
        logger.info(f"Mock Recommendation Engine initialized with DB: {self.db_path}")
    
    def get_real_user_behavior(self, user_id: int):
        """ENHANCED: Real-time behavior với cache busting - cập nhật ngay lập tức"""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            if not os.path.exists(self.db_path):
                logger.warning(f"Database not found: {self.db_path}")
                return {}, {}
            
            # ✅ FRESH CONNECTION MỖI LẦN (no caching)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ✅ INSTANT UPDATE: Giảm xuống 1 ngày và tăng limit để catch mọi recent interactions
            # ✅ ORDER BY timestamp DESC để lấy interactions mới nhất trước
            query = """
                SELECT ui.interaction_type, ui.details, p.category, ui.timestamp, p.id, p.name
                FROM user_interaction ui
                LEFT JOIN product p ON ui.product_id = p.id
                WHERE ui.user_id = ? AND ui.timestamp >= datetime('now', '-1 days')
                ORDER BY ui.timestamp DESC
                LIMIT 100
            """
            
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()
            
            clicked_categories = {}
            viewed_categories = {}
            recent_products = []  # Track recent interactions
            
            # 🎯 INSTANT SCORING với position weight: Click gần nhất = ƯU TIÊN TUYỆT ĐỐI
            for i, (interaction_type, details, category, timestamp, product_id, product_name) in enumerate(results):
                if not category:
                    continue
                
                # 🔥 POSITION WEIGHT: Click đầu tiên (gần nhất) = weight cực cao
                position_weight = max(10 - i * 0.1, 1.0)  # 10, 9.9, 9.8, 9.7, ..., 1.0
                
                # ✅ SUPER ENHANCED TIME WEIGHTING - INSTANT response cho clicks mới nhất
                try:
                    # Parse timestamp
                    interaction_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    seconds_ago = (datetime.now() - interaction_time.replace(tzinfo=None)).total_seconds()
                    
                    # ✅ SECONDS-BASED weighting cho INSTANT response
                    if seconds_ago <= 30:      # Last 30 seconds
                        time_weight = 10.0     # INSTANT BOOST - clicks vừa mới
                    elif seconds_ago <= 300:  # Last 5 minutes
                        time_weight = 8.0      # VERY FRESH
                    elif seconds_ago <= 3600: # Last 1 hour  
                        time_weight = 5.0      # Recent
                    elif seconds_ago <= 86400: # Last 1 day
                        time_weight = 2.0      # Normal
                    else:
                        time_weight = 1.0      # Old
                        
                    # 🔥 COMBINED WEIGHT = position × time
                    final_weight = position_weight * time_weight
                        
                except:
                    final_weight = position_weight  # Default if timestamp parsing fails
                
                # ✅ VERY HIGH BASE SCORES cho instant dominance - BAO GỒM VIEWS
                if interaction_type in ['click', 'product_click', 'recommendation_click']:
                    score = 15 * final_weight  # Clicks = highest priority
                    clicked_categories[category] = clicked_categories.get(category, 0) + score
                    
                    # Track recent products for fallback
                    if product_id and len(recent_products) < 20:
                        recent_products.append({
                            'id': product_id,
                            'name': product_name,
                            'category': category,
                            'score': score,
                            'seconds_ago': seconds_ago
                        })
                        
                elif interaction_type in ['view', 'product_view']:
                    score = 12 * final_weight  # Views = high priority (INCREASED from 8)
                    clicked_categories[category] = clicked_categories.get(category, 0) + score  # ✅ ADD TO CLICKED (not viewed)
                elif interaction_type == 'search':
                    score = 4 * final_weight  # Search = medium priority
                    viewed_categories[category] = viewed_categories.get(category, 0) + score
            
            conn.close()
            
            # ✅ LOG CHI TIẾT ĐỂ DEBUG REAL-TIME UPDATES
            logger.info(f"🔄 REAL-TIME UPDATE User {user_id}: clicks={clicked_categories}, views={viewed_categories}")
            if recent_products:
                logger.info(f"📱 Most recent: {recent_products[0]['name']} ({recent_products[0]['seconds_ago']:.0f}s ago)")
            
            return clicked_categories, viewed_categories
            
        except Exception as e:
            logger.error(f"❌ Real behavior error: {e}")
            return {}, {}
    
    def get_latest_clicked_category(self, user_id: int):
        """Lấy category từ click/view GẦN NHẤT (trong 5 phút) - INSTANT SWITCH"""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            if not os.path.exists(self.db_path):
                return None
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 🔥 LẤY INTERACTION GẦN NHẤT TRONG 5 PHÚT - BAOỒM CẢ VIEWS
            query = """
                SELECT p.category, ui.timestamp, ui.interaction_type
                FROM user_interaction ui
                LEFT JOIN product p ON ui.product_id = p.id
                WHERE ui.user_id = ? 
                AND ui.interaction_type IN ('click', 'view', 'product_click', 'product_view', 'recommendation_click')
                AND ui.timestamp >= datetime('now', '-5 minutes')
                AND p.category IS NOT NULL
                ORDER BY ui.timestamp DESC
                LIMIT 1
            """
            
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                latest_category, timestamp, interaction_type = result
                logger.info(f"🎯 LATEST CLICK: User {user_id} → {latest_category} ({interaction_type})")
                return latest_category
            else:
                logger.info(f"⚠️ No recent clicks in last 5 minutes for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Get latest category error: {e}")
            return None
    
    def get_recommendations_for_user(self, user_id: int, num_recs: int = 10):
        """
        INSTANT CATEGORY SWITCH: Chỉ cần 1 click là đổi recommendations ngay
        - Luôn ưu tiên category từ click gần nhất (trong 5 phút)
        - 8 sản phẩm cùng loại + 2 sản phẩm khác loại
        """
        
        # ✅ LUÔN ĐỌC REAL DATA TRƯỚC (ưu tiên cao nhất)
        real_clicked_categories, real_viewed_categories = self.get_real_user_behavior(user_id)
        
        # ✅ ƯU TIÊN REAL DATA (NGAY CẢ CHỈ 1 INTERACTION)
        if real_clicked_categories or real_viewed_categories:
            clicked_categories = real_clicked_categories
            viewed_categories = real_viewed_categories
            data_source = "real_database_instant"
            
            # 🔥 INSTANT SWITCH: Lấy category từ click GẦN NHẤT (không cần so sánh điểm)
            latest_category = self.get_latest_clicked_category(user_id)
            
            if latest_category:
                # 🎯 SỬ DỤNG CATEGORY GẦN NHẤT LÀM MAIN CATEGORY
                main_category = latest_category
                logger.info(f"� INSTANT SWITCH: User {user_id} → {main_category} (from latest click)")
            else:
                # Fallback: category có điểm cao nhất
                main_category = max(clicked_categories.keys(), key=clicked_categories.get) if clicked_categories else None
                logger.info(f"📊 FALLBACK: User {user_id} → {main_category} (from highest score)")
                
        else:
            # ❌ CHỈ DÙNG MOCK KHI HOÀN TOÀN KHÔNG CÓ DATA
            logger.info(f"⚠️ FALLBACK: User {user_id} no real data found, using mock pattern")
            
            # Mock patterns cho demo (chỉ khi không có real data)
            user_patterns = {
                1: {
                    'clicked': {'Thực phẩm tươi sống': 15, 'Rau củ quả': 8},
                    'viewed': {'Trái cây tươi': 4, 'Thực phẩm khô & Gia vị': 2}
                },
                2: {
                    'clicked': {'Sản phẩm làm đẹp & Chăm sóc cá nhân': 12, 'Đồ gia dụng nhà bếp': 6},
                    'viewed': {'Bánh kẹo & Snacks': 4, 'Đồ uống & Nước giải khát': 2}
                },
                3: {
                    'clicked': {'Đồ gia dụng nhà bếp': 15, 'Trái cây tươi': 6},
                    'viewed': {'Sản phẩm làm đẹp & Chăm sóc cá nhân': 3, 'Thực phẩm khô & Gia vị': 2}
                },
                4: {
                    'clicked': {'Đồ uống & Nước giải khát': 12, 'Bánh kẹo & Snacks': 7},
                    'viewed': {'Trái cây tươi': 4, 'Đồ gia dụng nhà bếp': 3}
                }
            }
            
            if user_id in user_patterns:
                clicked_categories = user_patterns[user_id]['clicked']
                viewed_categories = user_patterns[user_id]['viewed']
                data_source = f"mock_pattern_user_{user_id}"
                main_category = max(clicked_categories.keys(), key=clicked_categories.get)
            else:
                # Tạo pattern ngẫu nhiên cho user mới
                import random
                random.seed(user_id)  # Consistent cho cùng user
                
                all_categories = ['Thực phẩm tươi sống', 'Đồ uống & Nước giải khát', 'Trái cây tươi', 
                                'Rau củ quả', 'Thực phẩm khô & Gia vị', 'Bánh kẹo & Snacks',
                                'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'Đồ gia dụng nhà bếp']
                
                main_categories = random.sample(all_categories, random.randint(2, 3))
                
                clicked_categories = {}
                viewed_categories = {}
                
                for i, cat in enumerate(main_categories):
                    clicked_categories[cat] = random.randint(6, 12) - i * 2
                    
                remaining_cats = [c for c in all_categories if c not in main_categories]
                for cat in random.sample(remaining_cats, min(2, len(remaining_cats))):
                    viewed_categories[cat] = random.randint(2, 5)
                
                data_source = f"generated_pattern_user_{user_id}"
                main_category = max(clicked_categories.keys(), key=clicked_categories.get)
        
        total_interactions = sum(clicked_categories.values()) + sum(viewed_categories.values())
        
        # ✅ CẦN ÍT NHẤT 1 INTERACTION
        if total_interactions < 1:
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': [],
                'total': 0,
                'analysis': {
                    'strategy_used': 'no_data_available',
                    'total_interactions': 0,
                    'data_source': data_source,
                    'note': f'User {user_id} chưa có interactions. Hãy click vào sản phẩm để nhận gợi ý instant!'
                }
            }
        
        if not main_category:
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': [],
                'total': 0,
                'analysis': {
                    'strategy_used': 'no_main_category',
                    'note': 'Không tìm thấy main category'
                }
            }
        
        logger.info(f"User {user_id}: Generating INSTANT recommendations from {data_source}")
        
        # 🎯 INSTANT STRATEGY: 8 sản phẩm cùng loại + 2 sản phẩm khác loại
        recommendations = []
        used_product_ids = set()
        
        # PHASE 1: Lấy 8 sản phẩm từ main category (latest clicked)
        main_category_products = [p for p in self.mock_products if p['category'] == main_category]
        
        # ✅ DEBUG: KIỂM TRA CATEGORY FILTERING
        logger.info(f"🔍 CATEGORY FILTER DEBUG:")
        logger.info(f"   Main category: '{main_category}'")
        logger.info(f"   Total mock products: {len(self.mock_products)}")
        logger.info(f"   Products in main category: {len(main_category_products)}")
        if len(main_category_products) > 0:
            logger.info(f"   Sample main products: {[p['name'] for p in main_category_products[:3]]}")
        
        # ✅ KIỂM TRA NẾU KHÔNG ĐỦ PRODUCTS TRONG MAIN CATEGORY
        if len(main_category_products) == 0:
            logger.warning(f"❌ KHÔNG CÓ PRODUCTS trong category: '{main_category}'")
            
            # Show available categories for debugging
            available_categories = list(set([p['category'] for p in self.mock_products]))
            logger.warning(f"❌ Available categories: {available_categories}")
            
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': [],
                'total': 0,
                'analysis': {
                    'strategy_used': 'no_products_in_category',
                    'main_category': main_category,
                    'available_categories': available_categories,
                    'note': f'Không tìm thấy sản phẩm trong category: {main_category}'
                }
            }
        
        # ✅ SHUFFLE dựa trên timestamp để có variability mỗi lần
        import random
        import time
        random.seed(user_id + int(time.time() / 60))  # Đổi mỗi phút để có variety
        shuffled_main = main_category_products.copy()
        random.shuffle(shuffled_main)
        
        # ✅ LẤY TỐI ĐA 8 PRODUCTS HOẶC TẤT CẢ NẾU ÍT HƠN 8
        target_main_products = min(8, len(main_category_products))
        
        for product in shuffled_main[:target_main_products]:
            if product['id'] not in used_product_ids:
                product_copy = product.copy()
                product_copy['reason'] = f"🔥 INSTANT: {main_category}"
                recommendations.append(product_copy)
                used_product_ids.add(product['id'])
        
        logger.info(f"✅ INSTANT: Added {len(recommendations)} products from main category: {main_category} (available: {len(main_category_products)})")
        
        # PHASE 2: Lấy 2 sản phẩm khác loại
        other_recommendations = []
        target_other_products = min(2, 10 - len(recommendations))  # Đảm bảo tổng không quá 10
        
        # Strategy 2a: Từ lịch sử recommend trước (nếu có)
        if user_id in self.user_recommendation_history:
            previous_recs = self.user_recommendation_history[user_id]
            for prev_rec in previous_recs[-10:]:  # Lấy 10 gợi ý gần nhất
                if prev_rec['category'] != main_category and prev_rec['id'] not in used_product_ids:
                    # Tìm product trong database
                    product = next((p for p in self.mock_products if p['id'] == prev_rec['id']), None)
                    if product and len(other_recommendations) < target_other_products:
                        product_copy = product.copy()
                        product_copy['reason'] = f"Từ lần gợi ý trước: {product['category']}"
                        other_recommendations.append(product_copy)
                        used_product_ids.add(product['id'])
        
        # Strategy 2b: Từ related categories nếu chưa đủ 2
        if len(other_recommendations) < target_other_products and main_category in self.category_relations:
            for related_cat in self.category_relations[main_category]:
                if len(other_recommendations) >= target_other_products:
                    break
                    
                related_products = [p for p in self.mock_products 
                                 if p['category'] == related_cat and p['id'] not in used_product_ids]
                
                if related_products:
                    # Shuffle related products
                    random.shuffle(related_products)
                    product = related_products[0]
                    product_copy = product.copy()
                    product_copy['reason'] = f"Liên quan đến {main_category}"
                    other_recommendations.append(product_copy)
                    used_product_ids.add(product['id'])
        
        # Strategy 2c: Từ viewed categories nếu vẫn chưa đủ
        if len(other_recommendations) < target_other_products:
            for category, score in sorted(viewed_categories.items(), key=lambda x: x[1], reverse=True):
                if len(other_recommendations) >= target_other_products or category == main_category:
                    continue
                    
                category_products = [p for p in self.mock_products 
                                   if p['category'] == category and p['id'] not in used_product_ids]
                
                if category_products:
                    random.shuffle(category_products)
                    product = category_products[0]
                    product_copy = product.copy()
                    product_copy['reason'] = f"Đã xem: {category}"
                    other_recommendations.append(product_copy)
                    used_product_ids.add(product['id'])
        
        # Strategy 2d: Fallback - bất kỳ sản phẩm nào khác
        if len(other_recommendations) < target_other_products:
            remaining_products = [p for p in self.mock_products 
                                if p['category'] != main_category and p['id'] not in used_product_ids]
            needed = target_other_products - len(other_recommendations)
            for product in remaining_products[:needed]:
                product_copy = product.copy()
                product_copy['reason'] = f"Khám phá: {product['category']}"
                other_recommendations.append(product_copy)
                used_product_ids.add(product['id'])
        
        # Combine final recommendations
        final_recommendations = recommendations + other_recommendations[:target_other_products]
        
        # ✅ LƯU LỊCH SỬ RECOMMENDATION CHO USER
        if user_id not in self.user_recommendation_history:
            self.user_recommendation_history[user_id] = []
        
        # Thêm recommendations mới vào lịch sử
        for rec in final_recommendations:
            self.user_recommendation_history[user_id].append({
                'id': rec['id'],
                'category': rec['category'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Giữ chỉ 50 recommendations gần nhất
        self.user_recommendation_history[user_id] = self.user_recommendation_history[user_id][-50:]
        
        # ✅ CHI TIẾT ANALYSIS ĐỂ DEBUG
        return {
            'status': 'success',
            'user_id': user_id,
            'recommendations': final_recommendations[:10],
            'total': len(final_recommendations[:10]),
            'analysis': {
                'main_category': main_category,
                'main_category_products': len(recommendations),
                'other_category_products': len(other_recommendations),
                'top_clicked_categories': clicked_categories,
                'top_viewed_categories': viewed_categories,
                'total_interactions': int(total_interactions),
                'strategy_used': 'instant_switch_8_plus_2',
                'data_source': data_source,
                'is_real_time': data_source.startswith('real_database'),
                'instant_switch': True,
                'latest_click_category': self.get_latest_clicked_category(user_id),
                'recommendation_breakdown': {
                    'same_category': len(recommendations),
                    'different_categories': len(other_recommendations),
                    'from_history': len([r for r in other_recommendations if 'lần gợi ý trước' in r.get('reason', '')]),
                    'from_related': len([r for r in other_recommendations if 'Liên quan' in r.get('reason', '')]),
                    'from_viewed': len([r for r in other_recommendations if 'Đã xem' in r.get('reason', '')]),
                    'from_discovery': len([r for r in other_recommendations if 'Khám phá' in r.get('reason', '')])
                },
                'note': f'� INSTANT SWITCH cho User {user_id}: {len(recommendations)} từ {main_category} + {len(other_recommendations)} từ categories khác'
            }
        }

# Initialize recommendation engine
if HAS_FULL_ENGINE:
    try:
        recommendation_api = RecommendationAPI()
        logger.info("✅ Full recommendation engine loaded")
    except Exception as e:
        logger.error(f"❌ Error loading full engine: {e}")
        recommendation_api = MockRecommendationEngine()
else:
    recommendation_api = MockRecommendationEngine()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'recommendation-api',
        'timestamp': datetime.utcnow().isoformat(),
        'engine_type': 'full' if HAS_FULL_ENGINE else 'mock'
    })

@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_user_recommendations(user_id):
    """Get recommendations for a specific user"""
    try:
        num_recs = request.args.get('num_recs', 10, type=int)  # Mặc định 10 thay vì 6
        
        logger.info(f"📝 Getting recommendations for user {user_id}, num_recs={num_recs}")
        
        # Get recommendations from engine
        result = recommendation_api.get_recommendations_for_user(user_id, num_recs)
        
        logger.info(f"✅ Generated {len(result.get('recommendations', []))} recommendations")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Error getting recommendations: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'recommendations': []
        }), 500

@app.route('/analyze/<int:user_id>', methods=['GET'])
def analyze_user_behavior(user_id):
    """Analyze user behavior"""
    try:
        days = request.args.get('days', 7, type=int)
        
        if hasattr(recommendation_api, 'analyze_user_behavior'):
            result = recommendation_api.analyze_user_behavior(user_id, days)
        else:
            # Mock analysis for testing
            result = {
                'clicked_categories': {'Thực phẩm tươi sống': 5, 'Trái cây tươi': 3},
                'viewed_categories': {'Đồ uống & Nước giải khát': 4, 'Rau củ quả': 2},
                'total_interactions': 14,
                'note': 'Mock analysis data for testing'
            }
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'analysis': result
        })
        
    except Exception as e:
        logger.error(f"❌ Error analyzing user behavior: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test', methods=['GET'])
def test_recommendations():
    """Test endpoint với user demo"""
    try:
        result = recommendation_api.get_recommendations_for_user(1, 6)
        return jsonify({
            'message': 'Test successful',
            'sample_result': result
        })
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return jsonify({
            'message': 'Test failed',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    
    print(f"🚀 Starting Recommendation API Server on port {port}")
    print(f"🔧 Engine type: {'Full' if HAS_FULL_ENGINE else 'Mock'}")
    print(f"📊 Endpoints available:")
    print(f"   GET /health - Health check")
    print(f"   GET /recommendations/<user_id> - Get user recommendations")
    print(f"   GET /analyze/<user_id> - Analyze user behavior")
    print(f"   GET /test - Test endpoint")
    
    app.run(host='0.0.0.0', port=port, debug=True)
