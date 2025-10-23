#!/usr/bin/env python3
"""
Debug real database interactions để xem user thực sự click vào gì
"""

import sqlite3
import os
from datetime import datetime

def debug_real_database():
    """Debug real database interactions"""
    print("🔍 DEBUGGING REAL DATABASE INTERACTIONS")
    print("="*60)
    
    db_path = os.path.abspath(os.path.join('web-app', 'instance', 'ecommerce.db'))
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Lấy tất cả interactions của users
        query = """
            SELECT ui.user_id, ui.interaction_type, ui.details, p.category, p.name, ui.timestamp
            FROM user_interaction ui
            LEFT JOIN product p ON ui.product_id = p.id
            WHERE ui.timestamp >= datetime('now', '-1 days')
            ORDER BY ui.user_id, ui.timestamp DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("❌ Không có interactions trong database")
            conn.close()
            return
        
        # Group by user
        user_interactions = {}
        for user_id, interaction_type, details, category, product_name, timestamp in results:
            if user_id not in user_interactions:
                user_interactions[user_id] = []
            user_interactions[user_id].append({
                'type': interaction_type,
                'details': details,
                'category': category,
                'product_name': product_name,
                'timestamp': timestamp
            })
        
        # Display results
        for user_id in sorted(user_interactions.keys()):
            interactions = user_interactions[user_id]
            print(f"\n👤 USER {user_id} ({len(interactions)} interactions):")
            print("-" * 40)
            
            # Count by category
            category_counts = {}
            latest_clicks = []
            
            for interaction in interactions[:10]:  # Show latest 10
                category = interaction['category'] or 'Unknown'
                interaction_type = interaction['type']
                
                if interaction_type in ['click', 'product_click', 'recommendation_click']:
                    category_counts[category] = category_counts.get(category, 0) + 1
                    if len(latest_clicks) < 3:
                        latest_clicks.append({
                            'category': category,
                            'product': interaction['product_name'],
                            'timestamp': interaction['timestamp']
                        })
                
                print(f"   {interaction_type}: {interaction['product_name']} ({category})")
                print(f"      Time: {interaction['timestamp']}")
            
            print(f"\n📊 Category click counts:")
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {category}: {count} clicks")
            
            print(f"\n🎯 Latest clicks (for instant switch):")
            for click in latest_clicks:
                print(f"   {click['category']}: {click['product']} ({click['timestamp']})")
            
            if category_counts:
                main_category = max(category_counts.keys(), key=category_counts.get)
                print(f"\n✅ Expected main category: {main_category}")
            else:
                print(f"\n⚠️ No clicks found - will use mock pattern")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_real_database()