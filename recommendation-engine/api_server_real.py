from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from collections import Counter

# Import simplified recommendation engine
try:
    from simple_recommendation import SimpleRecommendationEngine
    HAS_FULL_ENGINE = True
    print("✅ Using SimpleRecommendationEngine (100% real data)")
except ImportError:
    HAS_FULL_ENGINE = False
    print("⚠️ Warning: SimpleRecommendationEngine not available")

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDataRecommendationAPI:
    """✅ 100% Real Data - Không có mock data"""
    
    def __init__(self):
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'web-app', 'instance', 'ecommerce.db'))
        
        # Category relations for recommendations
        self.category_relations = {
            'Thực phẩm tươi sống': ['Rau củ quả', 'Thực phẩm khô & Gia vị', 'Đồ gia dụng nhà bếp'],
            'Đồ uống & Nước giải khát': ['Bánh kẹo & Snacks', 'Trái cây tươi', 'Thực phẩm tươi sống'],
            'Trái cây tươi': ['Đồ uống & Nước giải khát', 'Rau củ quả', 'Sản phẩm làm đẹp & Chăm sóc cá nhân'],
            'Rau củ quả': ['Thực phẩm tươi sống', 'Trái cây tươi', 'Thực phẩm khô & Gia vị'],
            'Thực phẩm khô & Gia vị': ['Thực phẩm tươi sống', 'Rau củ quả', 'Đồ gia dụng nhà bếp'],
            'Đồ gia dụng nhà bếp': ['Thực phẩm khô & Gia vị', 'Thực phẩm tươi sống', 'Đồ dùng gia đình'],
            'Bánh kẹo & Snacks': ['Đồ uống & Nước giải khát', 'Trái cây tươi', 'Sản phẩm làm đẹp & Chăm sóc cá nhân'],
            'Sản phẩm làm đẹp & Chăm sóc cá nhân': ['Đồ dùng gia đình', 'Bánh kẹo & Snacks', 'Trái cây tươi'],
            'Đồ dùng gia đình': ['Đồ gia dụng nhà bếp', 'Sản phẩm làm đẹp & Chăm sóc cá nhân', 'Thực phẩm khô & Gia vị']
        }
        
        logger.info(f"✅ Real Data Recommendation API initialized with SQLite: {self.db_path}")
    
    def get_db_connection(self):
        """Get SQLite database connection"""
        if os.path.exists(self.db_path):
            return sqlite3.connect(self.db_path)
        else:
            logger.error(f"❌ Database not found: {self.db_path}")
            return None
    
    def get_user_interactions(self, user_id: int, days: int = 1):
        """✅ Lấy interactions THẬT từ database"""
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query = """
                SELECT ui.interaction_type, ui.details, ui.timestamp, 
                       p.category, p.id, p.name, p.price
                FROM user_interaction ui
                LEFT JOIN product p ON ui.product_id = p.id
                WHERE ui.user_id = ? AND ui.timestamp >= ?
                ORDER BY ui.timestamp DESC
                LIMIT 100
            """
            
            cursor.execute(query, (user_id, since_date))
            results = cursor.fetchall()
            conn.close()
            
            logger.info(f"✅ Found {len(results)} real interactions for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error fetching interactions: {e}")
            if conn:
                conn.close()
            return []
    
    def get_latest_clicked_category(self, user_id: int):
        """✅ Lấy category từ interaction GẦN NHẤT (30 phút) - BAO GỒM VIEW"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT p.category, ui.timestamp, ui.interaction_type, p.name
                FROM user_interaction ui
                LEFT JOIN product p ON ui.product_id = p.id
                WHERE ui.user_id = ? 
                AND ui.interaction_type IN ('click', 'view', 'product_click', 'product_view')
                AND ui.timestamp >= datetime('now', '-30 minutes')
                AND p.category IS NOT NULL
                ORDER BY ui.timestamp DESC
                LIMIT 1
            """
            
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                latest_category, timestamp, interaction_type, product_name = result
                logger.info(f"🎯 LATEST: User {user_id} → {product_name} ({latest_category})")
                return latest_category
            else:
                logger.info(f"⚠️ No recent interactions for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting latest category: {e}")
            if conn:
                conn.close()
            return None
    
    def get_products_from_db(self, category=None, limit=10, exclude_ids=None):
        """✅ Lấy sản phẩm THẬT từ database"""
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if category:
                query = "SELECT id, name, description, price, category, image_url, stock FROM product WHERE category = ?"
                params = [category]
            else:
                query = "SELECT id, name, description, price, category, image_url, stock FROM product WHERE 1=1"
                params = []
            
            if exclude_ids:
                placeholders = ','.join(['?'] * len(exclude_ids))
                query += f" AND id NOT IN ({placeholders})"
                params.extend(exclude_ids)
            
            query += " ORDER BY RANDOM() LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            products = []
            for row in rows:
                products.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'price': row[3],
                    'category': row[4],
                    'image_url': row[5],
                    'stock': row[6]
                })
            
            conn.close()
            logger.info(f"✅ Fetched {len(products)} real products (category: {category or 'all'})")
            return products
            
        except Exception as e:
            logger.error(f"❌ Error fetching products: {e}")
            if conn:
                conn.close()
            return []
    
    def get_recommendations_for_user(self, user_id: int, num_recs: int = 10):
        """✅ 100% Real Data Recommendations"""
        
        # 1. Get latest clicked category (instant switch)
        latest_category = self.get_latest_clicked_category(user_id)
        
        # 2. If no recent clicks, analyze all interactions
        if not latest_category:
            interactions = self.get_user_interactions(user_id, days=7)
            
            if not interactions:
                logger.info(f"⚠️ User {user_id} has NO interactions - no recommendations")
                return {
                    'status': 'success',
                    'user_id': user_id,
                    'recommendations': [],
                    'total': 0,
                    'analysis': {
                        'strategy_used': 'no_data',
                        'note': 'Chưa có tương tác. Hãy click vào sản phẩm để nhận gợi ý!'
                    }
                }
            
            # Count categories
            category_counter = Counter()
            for interaction in interactions:
                interaction_type, details, timestamp, category, product_id, product_name, price = interaction
                if category:
                    if interaction_type in ['click', 'product_click']:
                        category_counter[category] += 3
                    elif interaction_type in ['view', 'product_view']:
                        category_counter[category] += 2
                    else:
                        category_counter[category] += 1
            
            latest_category = category_counter.most_common(1)[0][0] if category_counter else None
        
        if not latest_category:
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': [],
                'total': 0,
                'analysis': {
                    'strategy_used': 'no_category',
                    'note': 'Không xác định được danh mục quan tâm'
                }
            }
        
        # 3. Get 8 products from main category + 2 from related categories
        recommendations = []
        used_ids = set()
        
        # 3a. Main category (8 products)
        main_products = self.get_products_from_db(latest_category, limit=8, exclude_ids=list(used_ids))
        for product in main_products:
            product['reason'] = f"🔥 {latest_category}"
            product['priority'] = 'main_category'
            recommendations.append(product)
            used_ids.add(product['id'])
        
        logger.info(f"✅ Added {len(main_products)} products from main category: {latest_category}")
        
        # 3b. Related categories (2 products)
        related_categories = self.category_relations.get(latest_category, [])
        for related_cat in related_categories[:2]:
            if len(recommendations) >= num_recs:
                break
            
            related_products = self.get_products_from_db(related_cat, limit=1, exclude_ids=list(used_ids))
            for product in related_products:
                product['reason'] = f"Liên quan: {related_cat}"
                product['priority'] = 'related_category'
                recommendations.append(product)
                used_ids.add(product['id'])
        
        logger.info(f"✅ Total recommendations: {len(recommendations)} products")
        
        return {
            'status': 'success',
            'user_id': user_id,
            'recommendations': recommendations[:num_recs],
            'total': len(recommendations[:num_recs]),
            'analysis': {
                'strategy_used': 'real_data_instant_switch',
                'main_category': latest_category,
                'data_source': '100% real SQLite database',
                'main_category_products': len(main_products),
                'related_category_products': len(recommendations) - len(main_products),
                'instant_switch': True,
                'note': f'✅ 100% dữ liệu thật: {len(main_products)} từ {latest_category} + {len(recommendations) - len(main_products)} liên quan'
            }
        }

# Initialize API
if HAS_FULL_ENGINE:
    try:
        recommendation_engine = SimpleRecommendationEngine()
        logger.info("✅ Using SimpleRecommendationEngine (100% real data)")
    except Exception as e:
        logger.error(f"❌ Error loading engine: {e}")
        recommendation_engine = RealDataRecommendationAPI()
else:
    recommendation_engine = RealDataRecommendationAPI()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'recommendation-api-real-data',
        'timestamp': datetime.utcnow().isoformat(),
        'data_source': '100% SQLite real data'
    })

@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_user_recommendations(user_id):
    """Get recommendations for a specific user - 100% REAL DATA"""
    try:
        num_recs = request.args.get('num_recs', 10, type=int)
        
        logger.info(f"📝 Getting REAL DATA recommendations for user {user_id}, num_recs={num_recs}")
        
        result = recommendation_engine.get_recommendations_for_user(user_id, num_recs)
        
        logger.info(f"✅ Generated {len(result.get('recommendations', []))} real recommendations")
        
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
    """Analyze user behavior - REAL DATA"""
    try:
        days = request.args.get('days', 7, type=int)
        
        if hasattr(recommendation_engine, 'analyze_user_behavior'):
            result = recommendation_engine.analyze_user_behavior(user_id, days)
        else:
            result = {
                'note': 'Analysis not available'
            }
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'analysis': result,
            'data_source': '100% real data'
        })
        
    except Exception as e:
        logger.error(f"❌ Error analyzing user behavior: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test', methods=['GET'])
def test_recommendations():
    """Test endpoint - REAL DATA"""
    try:
        result = recommendation_engine.get_recommendations_for_user(1, 10)
        return jsonify({
            'message': 'Test successful - 100% REAL DATA',
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
    
    print(f"🚀 Starting Recommendation API Server (100% REAL DATA) on port {port}")
    print(f"✅ Data source: SQLite database")
    print(f"📊 Endpoints available:")
    print(f"   GET /health - Health check")
    print(f"   GET /recommendations/<user_id> - Get user recommendations (REAL DATA)")
    print(f"   GET /analyze/<user_id> - Analyze user behavior (REAL DATA)")
    print(f"   GET /test - Test endpoint")
    
    app.run(host='0.0.0.0', port=port, debug=True)
