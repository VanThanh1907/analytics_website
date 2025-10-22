#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'web-app'))

from app import app, db, User, Product, UserInteraction
from datetime import datetime, timedelta
import json

def add_more_interactions():
    """Thêm nhiều interactions để test recommendations"""
    
    with app.app_context():
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            print("❌ Test user không tồn tại")
            return
        
        # Thêm nhiều interactions về gạo và thực phẩm
        new_interactions = [
            # Nhiều clicks vào gạo
            UserInteraction(
                user_id=test_user.id,
                product_id=1,  # Gạo ST25
                interaction_type='product_click',
                details={'action': 'view_product', 'source': 'search'},
                timestamp=datetime.utcnow() - timedelta(minutes=2)
            ),
            UserInteraction(
                user_id=test_user.id,
                product_id=1,  # Gạo ST25
                interaction_type='product_view',
                details={'action': 'view_details', 'time_spent': 45},
                timestamp=datetime.utcnow() - timedelta(minutes=1)
            ),
            # Search nhiều lần cho gạo
            UserInteraction(
                user_id=test_user.id,
                product_id=None,
                interaction_type='search',
                details={'query': 'gạo st25', 'results_count': 3},
                timestamp=datetime.utcnow() - timedelta(seconds=30)
            ),
            UserInteraction(
                user_id=test_user.id,
                product_id=None,
                interaction_type='search',
                details={'query': 'gạo thơm', 'results_count': 5},
                timestamp=datetime.utcnow() - timedelta(seconds=15)
            ),
            # Click vào category thực phẩm
            UserInteraction(
                user_id=test_user.id,
                product_id=None,
                interaction_type='category_view',
                details={'category': 'Thực phẩm tươi sống', 'products_viewed': 8},
                timestamp=datetime.utcnow()
            ),
        ]
        
        for interaction in new_interactions:
            db.session.add(interaction)
        
        db.session.commit()
        print(f"✅ Đã thêm {len(new_interactions)} interactions mới cho user {test_user.id}")
        
        # Hiển thị tất cả interactions
        all_interactions = UserInteraction.query.filter_by(user_id=test_user.id).order_by(UserInteraction.timestamp.desc()).all()
        print(f"\n📊 Tổng cộng {len(all_interactions)} interactions cho user {test_user.id}:")
        for i, interaction in enumerate(all_interactions, 1):
            product_info = f"Product: {interaction.product_id}" if interaction.product_id else "No product"
            details = interaction.details.get('query', '') if interaction.details and 'query' in interaction.details else ''
            if details:
                details = f"'{details}'"
            print(f"  {i}. {interaction.interaction_type} - {product_info} {details} - {interaction.timestamp}")

if __name__ == "__main__":
    add_more_interactions()
    print("\n🎯 Bây giờ hãy vào http://localhost:5000/recommendations để xem kết quả!")
    print("   Hoặc test API: curl http://localhost:5001/recommendations/1")