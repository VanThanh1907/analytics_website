import redis
import json
import sqlite3  # Thay đổi từ psycopg2 sang sqlite3
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any
from collections import Counter, defaultdict
import os

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaBasedRecommendationEngine:
    def __init__(self):
        # Kết nối Redis
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'), 
                port=6379, 
                decode_responses=True
            )
        except:
            logger.warning("Không thể kết nối Redis, sử dụng fallback")
            self.redis_client = None
        
        # Database connection - sử dụng SQLite như web app
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'web-app', 'instance', 'ecommerce.db')
        
        # Mapping danh mục liên quan dựa trên logic kinh doanh
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
        
        logger.info("Kafka-based Recommendation Engine đã khởi tạo")

    def get_db_connection(self):
        """Lấy kết nối SQLite database"""
        try:
            if os.path.exists(self.db_path):
                return sqlite3.connect(self.db_path)
            else:
                logger.warning(f"Database file not found: {self.db_path}")
                return None
        except Exception as e:
            logger.error(f"Không thể kết nối SQLite database: {e}")
            return None

    def analyze_user_behavior_from_kafka(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """Phân tích hành vi người dùng từ dữ liệu đã được Kafka xử lý và lưu trong DB"""
        behavior = {
            'clicked_categories': Counter(),
            'viewed_categories': Counter(), 
            'searched_categories': Counter(),
            'favorite_products': [],
            'recent_interactions': [],  # Tất cả interactions
            'recent_clicks': [],        # Chỉ clicks, ưu tiên cao nhất
            'shopping_patterns': defaultdict(int)
        }
        
        conn = self.get_db_connection()
        if not conn:
            return behavior
        
        try:
            cursor = conn.cursor()
            
            # Lấy tương tác trong N ngày gần đây
            since_date = datetime.now() - timedelta(days=days)
            
            # Query interactions từ database (đã được Kafka processor lưu vào)
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
            interactions = cursor.fetchall()
            
            # Phân tích từng interaction
            for interaction in interactions:
                interaction_type, details, timestamp, category, product_id, product_name, price = interaction
                
                if not category:
                    continue
                
                # Parse details JSON nếu có
                interaction_details = {}
                if details:
                    try:
                        interaction_details = json.loads(details) if isinstance(details, str) else details
                    except:
                        interaction_details = {}
                
                # Tính điểm cho từng loại tương tác
                if interaction_type in ['click', 'product_click']:
                    behavior['clicked_categories'][category] += 3  # Điểm cao cho click
                    if interaction_details.get('action') == 'add_to_cart':
                        behavior['clicked_categories'][category] += 5  # Điểm rất cao cho add to cart
                        behavior['shopping_patterns']['add_to_cart'] += 1
                    
                    # Lưu click riêng biệt để ưu tiên
                    behavior['recent_clicks'].append({
                        'product_id': product_id,
                        'product_name': product_name,
                        'category': category,
                        'timestamp': timestamp,
                        'price': price,
                        'interaction_type': 'click'
                    })
                
                elif interaction_type in ['view', 'product_view']:
                    behavior['viewed_categories'][category] += 2  # Điểm trung bình cho view
                    behavior['recent_interactions'].append({
                        'product_id': product_id,
                        'product_name': product_name,
                        'category': category,
                        'timestamp': timestamp,
                        'price': price
                    })
                
                elif interaction_type == 'search':
                    behavior['searched_categories'][category] += 1  # Điểm thấp cho search
                    search_query = interaction_details.get('query', '')
                    if search_query:
                        behavior['shopping_patterns'][f'search:{search_query}'] += 1
                
                elif interaction_type == 'category_view':
                    behavior['viewed_categories'][category] += 1
            
            # Xác định sản phẩm yêu thích (nhiều tương tác nhất)
            product_interactions = defaultdict(int)
            for interaction in behavior['recent_interactions']:
                product_interactions[interaction['product_id']] += 1
            
            # Lấy top 5 sản phẩm có nhiều tương tác nhất
            top_products = sorted(product_interactions.items(), key=lambda x: x[1], reverse=True)[:5]
            behavior['favorite_products'] = [prod_id for prod_id, count in top_products]
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Lỗi phân tích behavior: {e}")
            if conn:
                conn.close()
        
        return behavior

    def get_recommendations_for_user(self, user_id: int, num_recs: int = 6) -> Dict[str, Any]:
        """Tạo gợi ý dựa trên phân tích Kafka data - ưu tiên lần click gần nhất"""
        try:
            # 1. Phân tích hành vi từ Kafka data
            behavior = self.analyze_user_behavior_from_kafka(user_id)
            
            recommendations = []
            recommendation_reasons = []
            
            # 2. Strategy: PRIORITY - Gợi ý từ danh mục của lần click GẦN NHẤT
            recent_clicks = behavior.get('recent_clicks', [])
            if recent_clicks:
                # Lấy danh mục của lần click gần nhất (đầu tiên trong list đã sắp xếp DESC)
                latest_click_category = recent_clicks[0].get('category')
                if latest_click_category:
                    print(f"🎯 Latest CLICK category: {latest_click_category}")
                    
                    # Lấy 3-4 sản phẩm từ danh mục vừa click
                    latest_category_products = self._get_trending_products_from_category(
                        latest_click_category, 
                        limit=4,
                        exclude_products=[]
                    )
                    for product in latest_category_products:
                        product['reason'] = f"Dựa trên lần click gần nhất: {latest_click_category}"
                        product['priority'] = 'latest_click'
                        recommendations.append(product)
                        recommendation_reasons.append(f"Click gần nhất: {latest_click_category}")
                    
                    print(f"✅ Added {len(latest_category_products)} products from latest CLICK category")
            
            # Fallback: Nếu không có click, dùng view gần nhất
            elif behavior.get('recent_interactions', []):
                latest_interaction = behavior['recent_interactions'][0]
                latest_category = latest_interaction.get('category')
                if latest_category:
                    print(f"🎯 Latest VIEW category: {latest_category}")
                    
                    latest_category_products = self._get_trending_products_from_category(
                        latest_category, 
                        limit=3,
                        exclude_products=[]
                    )
                    for product in latest_category_products:
                        product['reason'] = f"Dựa trên lần xem gần nhất: {latest_category}"
                        product['priority'] = 'latest_view'
                        recommendations.append(product)
                        recommendation_reasons.append(f"Xem gần nhất: {latest_category}")
            
            # 3. Strategy: Gợi ý từ danh mục được click nhiều nhất (nếu chưa đủ)
            if len(recommendations) < num_recs:
                top_clicked_categories = behavior['clicked_categories'].most_common(3)
                used_categories = set()
                
                # Đánh dấu danh mục đã dùng cho latest click/view
                if recent_clicks:
                    used_categories.add(recent_clicks[0].get('category'))
                elif behavior.get('recent_interactions', []):
                    used_categories.add(behavior['recent_interactions'][0].get('category'))
                
                for category, click_count in top_clicked_categories:
                    if len(recommendations) >= num_recs:
                        break
                        
                    # Skip nếu đã có từ latest click/view
                    if category in used_categories:
                        continue
                        
                    category_products = self._get_trending_products_from_category(
                        category, 
                        limit=2,
                        exclude_products=[r.get('id') for r in recommendations if r.get('id')]
                    )
                    for product in category_products:
                        product['reason'] = f"Bạn quan tâm đến {category} ({click_count} lần click)"
                        product['priority'] = 'frequent_category'
                        recommendations.append(product)
                        recommendation_reasons.append(f"Quan tâm: {category}")
                    
                    used_categories.add(category)
                    if len(recommendations) >= num_recs:
                        break
            
            # 3. Strategy: Gợi ý từ danh mục liên quan
            if len(recommendations) < num_recs:
                related_categories = set()
                for category, _ in behavior['clicked_categories'].most_common(2):
                    if category in self.category_relations:
                        related_categories.update(self.category_relations[category][:2])
                
                for category in list(related_categories)[:3]:
                    if len(recommendations) >= num_recs:
                        break
                    
                    related_products = self._get_trending_products_from_category(
                        category,
                        limit=1,
                        exclude_products=[r.get('id') for r in recommendations if r.get('id')]
                    )
                    for product in related_products:
                        product['reason'] = f"Liên quan đến sở thích của bạn về {category}"
                        recommendations.append(product)
                        recommendation_reasons.append(f"Gợi ý từ {category}")
            
            # 4. Strategy: Sản phẩm tương tự với những gì đã xem
            if len(recommendations) < num_recs and behavior['favorite_products']:
                similar_products = self._get_similar_products(behavior['favorite_products'][:3])
                for product in similar_products:
                    if len(recommendations) >= num_recs:
                        break
                    if product.get('id') not in [r.get('id') for r in recommendations]:
                        product['reason'] = "Tương tự sản phẩm bạn đã quan tâm"
                        recommendations.append(product)
                        recommendation_reasons.append("Sản phẩm tương tự")
            
            # 5. Fallback: Sản phẩm trending nếu chưa đủ
            if len(recommendations) < num_recs:
                trending_products = self._get_global_trending_products(
                    limit=num_recs - len(recommendations),
                    exclude_products=[r.get('id') for r in recommendations if r.get('id')]
                )
                for product in trending_products:
                    product['reason'] = "Sản phẩm đang được quan tâm nhiều"
                    recommendations.append(product)
                    recommendation_reasons.append("Đang thịnh hành")
            
            # Cache kết quả
            self._cache_recommendations(user_id, recommendations)
            
            # Chuẩn bị response với strategy details
            strategy_details = []
            
            # Xác định strategy chính được sử dụng
            if behavior.get('recent_clicks'):
                primary_strategy = "latest_click_based"
                latest_category = behavior['recent_clicks'][0].get('category')
                strategy_details.append(f"Ưu tiên danh mục click gần nhất: {latest_category}")
            elif behavior.get('recent_interactions'):
                primary_strategy = "latest_view_based" 
                latest_category = behavior['recent_interactions'][0].get('category')
                strategy_details.append(f"Dựa trên danh mục xem gần nhất: {latest_category}")
            elif behavior['clicked_categories']:
                primary_strategy = "frequent_clicks_based"
                strategy_details.append("Dựa trên danh mục được click nhiều")
            elif behavior['viewed_categories']:
                primary_strategy = "frequent_views_based"
                strategy_details.append("Dựa trên danh mục được xem nhiều")
            else:
                primary_strategy = "trending_based"
                strategy_details.append("Sản phẩm đang thịnh hành")
            
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': recommendations[:num_recs],
                'total': len(recommendations[:num_recs]),
                'analysis': {
                    'strategy_used': primary_strategy,
                    'strategy_details': strategy_details,
                    'recent_clicks_count': len(behavior.get('recent_clicks', [])),
                    'recent_interactions_count': len(behavior.get('recent_interactions', [])),
                    'top_clicked_categories': dict(behavior['clicked_categories'].most_common(3)),
                    'top_viewed_categories': dict(behavior['viewed_categories'].most_common(3)),
                    'total_interactions': sum(behavior['clicked_categories'].values()) + sum(behavior['viewed_categories'].values()),
                    'recommendation_reasons': recommendation_reasons[:num_recs],
                    'latest_click_category': behavior['recent_clicks'][0].get('category') if behavior.get('recent_clicks') else None,
                    'latest_interaction_category': behavior['recent_interactions'][0].get('category') if behavior.get('recent_interactions') else None
                }
            }
            
        except Exception as e:
            logger.error(f"Lỗi tạo recommendations: {e}")
            return self._get_fallback_recommendations(user_id, num_recs)

    def _get_trending_products_from_category(self, category: str, limit: int = 5, exclude_products: List[int] = None) -> List[Dict]:
        """Lấy sản phẩm trending từ danh mục cụ thể"""
        exclude_products = exclude_products or []
        
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            # Query sản phẩm có nhiều tương tác nhất trong category
            exclude_clause = ""
            params = [category]
            
            if exclude_products:
                exclude_clause = f"AND p.id NOT IN ({','.join(['%s'] * len(exclude_products))})"
                params.extend(exclude_products)
            
            query = f"""
                SELECT p.id, p.name, p.description, p.price, p.category, p.image_url, p.stock,
                       COUNT(ui.id) as interaction_count
                FROM products p
                LEFT JOIN user_interactions ui ON p.id = ui.product_id 
                    AND ui.timestamp >= NOW() - INTERVAL '7 days'
                WHERE p.category = %s {exclude_clause}
                GROUP BY p.id, p.name, p.description, p.price, p.category, p.image_url, p.stock
                ORDER BY interaction_count DESC, p.created_at DESC
                LIMIT %s
            """
            params.append(limit)
            
            cursor.execute(query, params)
            products = cursor.fetchall()
            
            result = []
            for product in products:
                result.append({
                    'id': product[0],
                    'name': product[1],
                    'description': product[2],
                    'price': product[3],
                    'category': product[4],
                    'image_url': product[5],
                    'stock': product[6],
                    'interaction_count': product[7]
                })
            
            cursor.close()
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"Lỗi lấy trending products từ category {category}: {e}")
            if conn:
                conn.close()
            return []

    def _get_similar_products(self, product_ids: List[int], limit: int = 3) -> List[Dict]:
        """Lấy sản phẩm tương tự dựa trên cùng category"""
        if not product_ids:
            return []
        
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            # Lấy categories của các sản phẩm đã tương tác
            query = "SELECT DISTINCT category FROM products WHERE id = ANY(%s)"
            cursor.execute(query, (product_ids,))
            categories = [row[0] for row in cursor.fetchall()]
            
            if not categories:
                cursor.close()
                conn.close()
                return []
            
            # Lấy sản phẩm từ các category này (trừ sản phẩm đã tương tác)
            placeholders = ','.join(['%s'] * len(product_ids))
            query = f"""
                SELECT id, name, description, price, category, image_url, stock
                FROM products 
                WHERE category = ANY(%s) 
                AND id NOT IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            params = [categories] + product_ids + [limit]
            cursor.execute(query, params)
            products = cursor.fetchall()
            
            result = []
            for product in products:
                result.append({
                    'id': product[0],
                    'name': product[1],
                    'description': product[2],
                    'price': product[3],
                    'category': product[4],
                    'image_url': product[5],
                    'stock': product[6]
                })
            
            cursor.close()
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"Lỗi lấy similar products: {e}")
            if conn:
                conn.close()
            return []

    def _get_global_trending_products(self, limit: int = 5, exclude_products: List[int] = None) -> List[Dict]:
        """Lấy sản phẩm trending toàn hệ thống"""
        exclude_products = exclude_products or []
        
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            exclude_clause = ""
            params = []
            
            if exclude_products:
                exclude_clause = f"WHERE p.id NOT IN ({','.join(['%s'] * len(exclude_products))})"
                params.extend(exclude_products)
            
            query = f"""
                SELECT p.id, p.name, p.description, p.price, p.category, p.image_url, p.stock,
                       COUNT(ui.id) as interaction_count
                FROM products p
                LEFT JOIN user_interactions ui ON p.id = ui.product_id 
                    AND ui.timestamp >= NOW() - INTERVAL '3 days'
                {exclude_clause}
                GROUP BY p.id, p.name, p.description, p.price, p.category, p.image_url, p.stock
                ORDER BY interaction_count DESC, RANDOM()
                LIMIT %s
            """
            params.append(limit)
            
            cursor.execute(query, params)
            products = cursor.fetchall()
            
            result = []
            for product in products:
                result.append({
                    'id': product[0],
                    'name': product[1],
                    'description': product[2],
                    'price': product[3],
                    'category': product[4],
                    'image_url': product[5],
                    'stock': product[6],
                    'interaction_count': product[7]
                })
            
            cursor.close()
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"Lỗi lấy global trending products: {e}")
            if conn:
                conn.close()
            return []

    def _cache_recommendations(self, user_id: int, recommendations: List[Dict]):
        """Cache recommendations vào Redis"""
        if not self.redis_client:
            return
        
        try:
            cache_key = f"recommendations:user:{user_id}"
            product_ids = [r['id'] for r in recommendations]
            
            # Cache product IDs
            self.redis_client.setex(cache_key, 3600, json.dumps(product_ids))  # 1 giờ
            
            # Cache chi tiết recommendations  
            details_key = f"recommendations:details:user:{user_id}"
            self.redis_client.setex(details_key, 3600, json.dumps(recommendations, default=str))
            
        except Exception as e:
            logger.error(f"Lỗi cache recommendations: {e}")

    def _get_fallback_recommendations(self, user_id: int, num_recs: int) -> Dict[str, Any]:
        """Fallback recommendations khi có lỗi"""
        try:
            trending = self._get_global_trending_products(limit=num_recs)
            for product in trending:
                product['reason'] = "Sản phẩm phổ biến"
            
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': trending,
                'total': len(trending),
                'analysis': {
                    'strategy_used': 'fallback_trending',
                    'note': 'Sử dụng sản phẩm trending do thiếu dữ liệu cá nhân'
                }
            }
        except Exception as e:
            logger.error(f"Lỗi fallback recommendations: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'recommendations': []
            }

# API wrapper cho Flask app
class RecommendationAPI:
    def __init__(self):
        self.engine = KafkaBasedRecommendationEngine()
        logger.info("RecommendationAPI đã khởi tạo với Kafka-based engine")
    
    def get_recommendations_for_user(self, user_id: int, num_recs: int = 6) -> Dict[str, Any]:
        """API endpoint chính để lấy recommendations"""
        return self.engine.get_recommendations_for_user(user_id, num_recs)
    
    def analyze_user_behavior(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """API endpoint để phân tích hành vi user"""
        return self.engine.analyze_user_behavior_from_kafka(user_id, days)

def main():
    """Test function"""
    api = RecommendationAPI()
    
    # Test với user_id = 1
    result = api.get_recommendations_for_user(1, 6)
    print("=== KAFKA-BASED RECOMMENDATIONS ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()