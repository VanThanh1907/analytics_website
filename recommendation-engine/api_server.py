from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
import os
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

# Mock recommendation engine for testing
class MockRecommendationEngine:
    def __init__(self):
        # Connect to SQLite database to read real interactions
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'web-app', 'instance', 'ecommerce.db'))
        
        # Mock data for testing
        self.mock_products = [
            {'id': 1, 'name': 'Gạo ST25 túi 5kg', 'category': 'Thực phẩm tươi sống', 'price': 180000},
            {'id': 15, 'name': 'Coca Cola lon 330ml', 'category': 'Đồ uống & Nước giải khát', 'price': 360000},
            {'id': 28, 'name': 'Cam tươi Việt Nam 1kg', 'category': 'Trái cây tươi', 'price': 45000},
            {'id': 35, 'name': 'Cải thảo 500g', 'category': 'Rau củ quả', 'price': 15000},
            {'id': 42, 'name': 'Hạt điều rang muối 200g', 'category': 'Thực phẩm khô & Gia vị', 'price': 85000},
            {'id': 58, 'name': 'Bánh quy chocolate 300g', 'category': 'Bánh kẹo & Snacks', 'price': 55000}
        ]
        
        self.category_relations = {
            'Thực phẩm tươi sống': ['Rau củ quả', 'Thực phẩm khô & Gia vị'],
            'Đồ uống & Nước giải khát': ['Bánh kẹo & Snacks', 'Trái cây tươi'],
            'Trái cây tươi': ['Đồ uống & Nước giải khát', 'Rau củ quả'],
            'Rau củ quả': ['Thực phẩm tươi sống', 'Trái cây tươi'],
            'Thực phẩm khô & Gia vị': ['Thực phẩm tươi sống', 'Đồ gia dụng nhà bếp'],
            'Bánh kẹo & Snacks': ['Đồ uống & Nước giải khát', 'Trái cây tươi']
        }
        
        logger.info(f"Mock Recommendation Engine initialized with DB: {self.db_path}")
    
    def get_real_user_behavior(self, user_id: int):
        """Đọc behavior thực tế từ SQLite database"""
        try:
            import sqlite3
            
            if not os.path.exists(self.db_path):
                logger.warning(f"Database not found: {self.db_path}")
                return {}, {}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query user interactions from last 7 days
            query = """
                SELECT ui.interaction_type, ui.details, p.category, COUNT(*) as count
                FROM user_interaction ui
                LEFT JOIN product p ON ui.product_id = p.id
                WHERE ui.user_id = ? AND ui.timestamp >= datetime('now', '-7 days')
                GROUP BY ui.interaction_type, p.category
                ORDER BY count DESC
            """
            
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()
            
            clicked_categories = {}
            viewed_categories = {}
            
            for interaction_type, details, category, count in results:
                if not category:
                    continue
                    
                if interaction_type in ['click', 'product_click', 'recommendation_click']:
                    clicked_categories[category] = clicked_categories.get(category, 0) + count * 3
                elif interaction_type in ['view', 'product_view']:
                    viewed_categories[category] = viewed_categories.get(category, 0) + count * 2
                elif interaction_type == 'search':
                    viewed_categories[category] = viewed_categories.get(category, 0) + count
            
            conn.close()
            
            logger.info(f"Real behavior for user {user_id}: clicks={clicked_categories}, views={viewed_categories}")
            return clicked_categories, viewed_categories
            
        except Exception as e:
            logger.error(f"Error reading real behavior: {e}")
            return {}, {}
    
    def get_recommendations_for_user(self, user_id: int, num_recs: int = 6):
        """Real recommendations dựa trên database thực tế"""
        
        # Đọc behavior thực tế từ database
        real_clicked_categories, real_viewed_categories = self.get_real_user_behavior(user_id)
        
        # Fallback to mock data nếu không có real data
        if not real_clicked_categories and not real_viewed_categories:
            # Mô phỏng behavior khác nhau cho từng user để test
            if user_id == 1:
                # User 1: Quan tâm thực phẩm và đồ uống
                mock_clicked_categories = {
                    'Thực phẩm tươi sống': 8,
                    'Đồ uống & Nước giải khát': 5,
                    'Trái cây tươi': 3
                }
                mock_viewed_categories = {
                    'Rau củ quả': 6,
                    'Thực phẩm khô & Gia vị': 4
                }
            elif user_id == 2:
                # User 2: Quan tâm đồ gia dụng và làm đẹp
                mock_clicked_categories = {
                    'Đồ gia dụng nhà bếp': 6,
                    'Sản phẩm làm đẹp & Chăm sóc cá nhân': 4,
                    'Đồ dùng gia đình': 3
                }
                mock_viewed_categories = {
                    'Bánh kẹo & Snacks': 3,
                    'Đồ uống & Nước giải khát': 2
                }
            elif user_id == 999:
                # User 999: User mới hoàn toàn - KHÔNG có data
                mock_clicked_categories = {}
                mock_viewed_categories = {}
            else:
                # User khác hoặc chưa đăng nhập: Mô phỏng có một ít behavior data
                mock_clicked_categories = {
                    'Thực phẩm tươi sống': 4,
                    'Trái cây tươi': 3,
                    'Đồ uống & Nước giải khát': 2
                }
                mock_viewed_categories = {
                    'Rau củ quả': 3,
                    'Bánh kẹo & Snacks': 2
                }
            
            # Sử dụng mock data
            mock_clicked_categories = mock_clicked_categories
            mock_viewed_categories = mock_viewed_categories
            data_source = "mock"
        else:
            # Sử dụng real data
            mock_clicked_categories = real_clicked_categories
            mock_viewed_categories = real_viewed_categories
            data_source = "real_database"
        
        # Kiểm tra xem có behavior data không
        total_interactions = sum(mock_clicked_categories.values()) + sum(mock_viewed_categories.values())
        
        logger.info(f"User {user_id}: {total_interactions} interactions from {data_source}")
        
        # Chỉ dựa vào Kafka behavior data - KHÔNG có fallback
        if total_interactions < 1:
            # Không có data gì - trả về empty với thông báo
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': [],
                'total': 0,
                'analysis': {
                    'strategy_used': 'no_data',
                    'total_interactions': 0,
                    'data_source': data_source,
                    'note': 'Chưa có dữ liệu hành vi từ Kafka. Hãy tương tác với sản phẩm để nhận gợi ý!'
                }
            }
        
        # Có đủ data - dùng behavior-based
        recommendations = []
        reasons = []
        
        # Strategy 1: Add products from clicked categories
        for category, click_count in mock_clicked_categories.items():
            category_products = [p for p in self.mock_products if p['category'] == category]
            for product in category_products:
                if len(recommendations) < num_recs:
                    product_copy = product.copy()
                    product_copy['reason'] = f"Bạn đã click {click_count} lần vào {category}"
                    recommendations.append(product_copy)
                    reasons.append(f"Quan tâm đến {category}")
        
        # Strategy 2: Add products from related categories
        if len(recommendations) < num_recs:
            for category in list(mock_clicked_categories.keys())[:2]:
                if category in self.category_relations:
                    for related_cat in self.category_relations[category][:1]:
                        related_products = [p for p in self.mock_products if p['category'] == related_cat]
                        for product in related_products:
                            if len(recommendations) < num_recs:
                                # Check if not already added
                                if not any(r['id'] == product['id'] for r in recommendations):
                                    product_copy = product.copy()
                                    product_copy['reason'] = f"Liên quan đến sở thích về {category}"
                                    recommendations.append(product_copy)
                                    reasons.append(f"Gợi ý từ {related_cat}")
        
        # Strategy 3: KHÔNG fill bằng trending - chỉ dựa vào behavior data
        # Nếu không đủ recommendations từ behavior thì trả về ít hơn
        
        return {
            'status': 'success',
            'user_id': user_id,
            'recommendations': recommendations[:num_recs],
            'total': len(recommendations[:num_recs]),
            'analysis': {
                'top_clicked_categories': mock_clicked_categories,
                'top_viewed_categories': mock_viewed_categories,
                'total_interactions': total_interactions,
                'strategy_used': 'kafka_behavior_only',
                'recommendation_reasons': reasons[:num_recs],
                'data_source': data_source,
                'note': f'Chỉ dựa vào dữ liệu hành vi từ {data_source} - KHÔNG có fallback'
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
        num_recs = request.args.get('num_recs', 6, type=int)
        
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
