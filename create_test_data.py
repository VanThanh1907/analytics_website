#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'web-app'))

from app import app, db, User, Product, UserInteraction
from datetime import datetime, timedelta
import json

def create_test_database():
    """Tạo database và dữ liệu test"""
    
    with app.app_context():
        # Tạo tất cả bảng
        db.create_all()
        print("✅ Database tables created")
        
        # Tạo user test nếu chưa có
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            test_user = User(username='testuser', email='test@example.com')
            test_user.set_password('123456')
            db.session.add(test_user)
            db.session.commit()
            print(f"✅ Created test user: {test_user.username} (ID: {test_user.id})")
        else:
            print(f"✅ Test user exists: {test_user.username} (ID: {test_user.id})")
        
        # Tạo sample interactions cho test user
        existing_interactions = UserInteraction.query.filter_by(user_id=test_user.id).count()
        if existing_interactions == 0:
            # Mô phỏng user click vào gạo và search
            sample_interactions = [
                # Click vào gạo (product_id=1)
                UserInteraction(
                    user_id=test_user.id,
                    product_id=1,
                    interaction_type='product_click',
                    details={'action': 'view_product', 'source': 'category'},
                    timestamp=datetime.utcnow() - timedelta(minutes=10)
                ),
                UserInteraction(
                    user_id=test_user.id,
                    product_id=1,
                    interaction_type='product_view',
                    details={'action': 'view_details', 'time_spent': 30},
                    timestamp=datetime.utcnow() - timedelta(minutes=8)
                ),
                # Search cho gạo
                UserInteraction(
                    user_id=test_user.id,
                    product_id=None,
                    interaction_type='search',
                    details={'query': 'gạo', 'results_count': 5},
                    timestamp=datetime.utcnow() - timedelta(minutes=5)
                ),
                # Click thêm vào một sản phẩm thực phẩm khác
                UserInteraction(
                    user_id=test_user.id,
                    product_id=3,  # Assuming another food product
                    interaction_type='product_click',
                    details={'action': 'view_product', 'source': 'search'},
                    timestamp=datetime.utcnow() - timedelta(minutes=3)
                ),
            ]
            
            for interaction in sample_interactions:
                db.session.add(interaction)
            
            db.session.commit()
            print(f"✅ Created {len(sample_interactions)} sample interactions for user {test_user.id}")
        else:
            print(f"✅ User {test_user.id} already has {existing_interactions} interactions")
        
        # Hiển thị user interactions
        interactions = UserInteraction.query.filter_by(user_id=test_user.id).all()
        print(f"\n📊 User {test_user.id} interactions:")
        for i, interaction in enumerate(interactions, 1):
            print(f"  {i}. {interaction.interaction_type} - Product: {interaction.product_id} - {interaction.timestamp}")
        
        return test_user.id

if __name__ == "__main__":
    user_id = create_test_database()
    print(f"\n🎯 Test user ID: {user_id}")
    print("Now you can login with: username=testuser, password=123456")
    print("Or test API with: curl http://localhost:5001/recommendations/{user_id}")