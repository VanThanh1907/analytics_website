#!/usr/bin/env python3
"""
Simplified Recommendation Engine sử dụng SQLite database
Ưu tiên lần click gần nhất
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleRecommendationEngine:
    def __init__(self):
        # Path to SQLite database
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'web-app', 'instance', 'ecommerce.db')
        
        # Mapping danh mục liên quan
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
        
        logger.info("Simple Recommendation Engine initialized with SQLite")

    def get_db_connection(self):
        """Kết nối SQLite database"""
        try:
            if os.path.exists(self.db_path):
                return sqlite3.connect(self.db_path)
            else:
                logger.warning(f"Database not found: {self.db_path}")
                return None
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None

    def analyze_user_behavior(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """Phân tích hành vi user từ SQLite database"""
        behavior = {
            'clicked_categories': Counter(),
            'viewed_categories': Counter(),
            'recent_clicks': [],        # Clicks only, sorted by time DESC
            'recent_interactions': [],  # All interactions, sorted by time DESC
            'favorite_products': []
        }
        
        conn = self.get_db_connection()
        if not conn:
            return behavior
        
        try:
            cursor = conn.cursor()
            
            # Lấy interactions trong 7 ngày gần đây
            since_date = datetime.now() - timedelta(days=days)
            
            query = """
                SELECT ui.interaction_type, ui.details, ui.timestamp, 
                       p.category, p.id, p.name, p.price
                FROM user_interaction ui
                LEFT JOIN product p ON ui.product_id = p.id
                WHERE ui.user_id = ? AND ui.timestamp >= ?
                ORDER BY ui.timestamp DESC
                LIMIT 100
            """
            
            cursor.execute(query, (user_id, since_date.isoformat()))
            interactions = cursor.fetchall()
            
            logger.info(f"Found {len(interactions)} interactions for user {user_id}")
            
            # Phân tích từng interaction
            for interaction in interactions:
                interaction_type, details_json, timestamp, category, product_id, product_name, price = interaction
                
                if not category:
                    continue
                
                # Parse details
                details = {}
                if details_json:
                    try:
                        details = json.loads(details_json) if isinstance(details_json, str) else details_json
                    except:
                        details = {}
                
                # Tạo interaction object
                interaction_obj = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'category': category,
                    'timestamp': timestamp,
                    'price': price,
                    'interaction_type': interaction_type
                }
                
                # ✅ Phân loại theo interaction type - VIEWS = CLICKS (same weight)
                if interaction_type in ['click', 'view', 'product_click', 'product_view']:
                    behavior['clicked_categories'][category] += 3
                    behavior['recent_clicks'].append(interaction_obj)
                    behavior['recent_interactions'].append(interaction_obj)
                    logger.info(f"✅ Recorded {interaction_type.upper()}: {category} for user {user_id}")
                    
                elif interaction_type == 'search':
                    behavior['viewed_categories'][category] += 1
                    behavior['recent_interactions'].append(interaction_obj)
                    logger.info(f"Recorded SEARCH: {category} for user {user_id}")
            
            # Tìm favorite products
            product_count = Counter()
            for interaction in behavior['recent_interactions']:
                if interaction['product_id']:
                    product_count[interaction['product_id']] += 1
            
            behavior['favorite_products'] = [pid for pid, count in product_count.most_common(5)]
            
            cursor.close()
            conn.close()
            
            logger.info(f"Behavior analysis for user {user_id}: {len(behavior['recent_clicks'])} clicks, {len(behavior['recent_interactions'])} total interactions")
            
        except Exception as e:
            logger.error(f"Error analyzing behavior: {e}")
            if conn:
                conn.close()
        
        return behavior

    def get_products_from_category(self, category: str, limit: int = 6, exclude_ids: List[int] = None) -> List[Dict]:
        """Lấy sản phẩm từ danh mục"""
        if exclude_ids is None:
            exclude_ids = []
        
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            # Build exclude clause
            exclude_clause = ""
            params = [category, limit]
            if exclude_ids:
                placeholders = ','.join(['?'] * len(exclude_ids))
                exclude_clause = f"AND id NOT IN ({placeholders})"
                params = [category] + exclude_ids + [limit]
            
            query = f"""
                SELECT id, name, description, price, category, image_url, stock
                FROM product 
                WHERE category = ?
                {exclude_clause}
                ORDER BY id DESC
                LIMIT ?
            """
            
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
            logger.error(f"Error getting products from category {category}: {e}")
            if conn:
                conn.close()
            return []

    def get_recommendations_for_user(self, user_id: int, num_recs: int = 10) -> Dict[str, Any]:
        """Tạo gợi ý - 8 sản phẩm cùng danh mục + 2 danh mục liên quan"""
        try:
            # 1. Phân tích hành vi user
            behavior = self.analyze_user_behavior(user_id)
            
            recommendations = []
            recommendation_reasons = []
            used_categories = set()
            
            # 2. STRATEGY MỚI: 8 sản phẩm cùng danh mục với lần click gần nhất
            if behavior['recent_clicks']:
                latest_click = behavior['recent_clicks'][0]  # Click gần nhất
                latest_category = latest_click['category']
                latest_product_name = latest_click['product_name']
                
                logger.info(f"🎯 Latest click for user {user_id}: {latest_product_name} ({latest_category})")
                
                # Lấy 8 sản phẩm CÙNG DANH MỤC với sản phẩm vừa click
                same_category_products = self.get_products_from_category(
                    latest_category, 
                    limit=8,
                    exclude_ids=[latest_click['product_id']]  # Loại trừ sản phẩm vừa click
                )
                for product in same_category_products:
                    product['reason'] = f"Cùng danh mục với '{latest_product_name}'"
                    product['priority'] = 'same_category'
                    recommendations.append(product)
                    recommendation_reasons.append(f"Cùng danh mục: {latest_category}")
                
                used_categories.add(latest_category)
                logger.info(f"✅ Added {len(same_category_products)} products from same category: {latest_category}")
                
                # 3. Thêm sản phẩm từ 2 DANH MỤC LIÊN QUAN
                related_categories = self.category_relations.get(latest_category, [])[:2]  # Lấy 2 danh mục liên quan đầu tiên
                
                for related_cat in related_categories:
                    if related_cat not in used_categories:
                        related_products = self.get_products_from_category(
                            related_cat,
                            limit=1,  # 1 sản phẩm từ mỗi danh mục liên quan
                            exclude_ids=[r['id'] for r in recommendations]
                        )
                        for product in related_products:
                            product['reason'] = f"Liên quan đến '{latest_product_name}' - từ {related_cat}"
                            product['priority'] = 'related_category'
                            recommendations.append(product)
                            recommendation_reasons.append(f"Liên quan: {related_cat}")
                        
                        used_categories.add(related_cat)
                        logger.info(f"✅ Added {len(related_products)} products from related category: {related_cat}")
            
            
            # 4. Fallback cho user không có click history
            else:
                logger.info(f"No click history for user {user_id}, using view-based recommendations")
                
                # Nếu có interactions (views), dùng category được xem nhiều nhất
                if behavior['recent_interactions']:
                    most_viewed_category = behavior['recent_interactions'][0]['category']
                    
                    # Lấy 6 sản phẩm từ danh mục được xem nhiều
                    viewed_products = self.get_products_from_category(most_viewed_category, limit=6)
                    for product in viewed_products:
                        product['reason'] = f"Dựa trên danh mục bạn đã xem: {most_viewed_category}"
                        product['priority'] = 'viewed_category'
                        recommendations.append(product)
                        recommendation_reasons.append(f"Đã xem: {most_viewed_category}")
                
                # Hoàn toàn không có data → fallback general
                else:
                    fallback_products = self.get_products_from_category('Thực phẩm tươi sống', limit=6)
                    for product in fallback_products:
                        product['reason'] = "Sản phẩm phổ biến"
                        product['priority'] = 'fallback'
                        recommendations.append(product)
                        recommendation_reasons.append("Phổ biến")
            
            # Determine strategy used
            if behavior['recent_clicks']:
                strategy = "same_category_plus_related"
                latest_click = behavior['recent_clicks'][0]
                strategy_details = [
                    f"8 sản phẩm cùng danh mục với '{latest_click['product_name']}'",
                    f"Sản phẩm từ 2 danh mục liên quan đến '{latest_click['category']}'"
                ]
            elif behavior['recent_interactions']:
                strategy = "view_based_fallback"
                strategy_details = ["Dựa trên danh mục đã xem"]
            else:
                strategy = "no_data_fallback"
                strategy_details = ["Sản phẩm phổ biến (chưa có dữ liệu hành vi)"]
            
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': recommendations[:num_recs],
                'total': len(recommendations[:num_recs]),
                'analysis': {
                    'strategy_used': strategy,
                    'strategy_details': strategy_details,
                    'recent_clicks_count': len(behavior['recent_clicks']),
                    'recent_interactions_count': len(behavior['recent_interactions']),
                    'top_clicked_categories': dict(behavior['clicked_categories'].most_common(3)),
                    'top_viewed_categories': dict(behavior['viewed_categories'].most_common(3)),
                    'total_interactions': sum(behavior['clicked_categories'].values()) + sum(behavior['viewed_categories'].values()),
                    'recommendation_reasons': recommendation_reasons[:num_recs],
                    'latest_click_category': behavior['recent_clicks'][0]['category'] if behavior['recent_clicks'] else None,
                    'latest_click_product': behavior['recent_clicks'][0]['product_name'] if behavior['recent_clicks'] else None,
                    'latest_interaction_category': behavior['recent_interactions'][0]['category'] if behavior['recent_interactions'] else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'recommendations': [],
                'total': 0
            }