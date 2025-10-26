from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from kafka import KafkaProducer
import json
import redis
import os
import sys
import requests
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///ecommerce.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Khởi tạo các extension
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Kết nối Redis
try:
    redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'), decode_responses=True)
except:
    redis_client = None

# Kết nối Kafka
try:
    kafka_producer = KafkaProducer(
        bootstrap_servers=[os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
except:
    kafka_producer = None

# Hàm gửi sự kiện tới Kafka
def send_to_kafka(topic, data):
    """Gửi dữ liệu tới Kafka topic"""
    if kafka_producer:
        try:
            kafka_producer.send(topic, data)
            kafka_producer.flush()
        except Exception as e:
            print(f"Lỗi gửi dữ liệu tới Kafka: {e}")
    else:
        print("Kafka producer không khả dụng")

def send_user_event(user_id, event_type, extra_data=None):
    """Gửi sự kiện người dùng tới Kafka"""
    event_data = {
        'user_id': user_id,
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'session_id': session.get('session_id', str(uuid.uuid4()))
    }
    
    if extra_data:
        event_data.update(extra_data)
    
    send_to_kafka('user_events', event_data)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(500))
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    interaction_type = db.Column(db.String(50), nullable=False)  # click, search, purchase, view
    details = db.Column(db.JSON)  # Thông tin chi tiết về tương tác
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Hàm gửi event tới Kafka và lưu vào database
def send_user_event(user_id, event_type, data):
    # 1. Gửi tới Kafka cho real-time processing  
    if kafka_producer:
        event = {
            'user_id': user_id,
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': session.get('session_id', str(uuid.uuid4()))
        }
        try:
            kafka_producer.send('user_events', value=event)
            kafka_producer.flush()
        except Exception as e:
            print(f"Lỗi gửi event tới Kafka: {e}")
    
    # 2. Lưu vào database cho recommendation engine
    try:
        # Xác định product_id từ data
        product_id = None
        if isinstance(data, dict):
            product_id = data.get('product_id') or data.get('product') or data.get('id')
        
        # Tạo interaction record
        interaction = UserInteraction(
            user_id=user_id,
            product_id=product_id,
            interaction_type=event_type,
            details=data if isinstance(data, dict) else {'info': str(data)},
            timestamp=datetime.utcnow()
        )
        
        db.session.add(interaction)
        db.session.commit()
        
    except Exception as e:
        print(f"Lỗi lưu interaction vào DB: {e}")
        db.session.rollback()

# Session tracking helper
def update_session_activity():
    """Update or create session activity for real-time tracking"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    user_id = current_user.id if current_user.is_authenticated else None
    
    try:
        # Update or insert session
        from sqlalchemy import text
        query = text("""
            INSERT INTO active_session (session_id, user_id, last_activity)
            VALUES (:session_id, :user_id, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) 
            DO UPDATE SET last_activity = CURRENT_TIMESTAMP, user_id = :user_id
        """)
        db.session.execute(query, {'session_id': session_id, 'user_id': user_id})
        db.session.commit()
    except Exception as e:
        print(f"Session tracking error: {e}")
        db.session.rollback()

# Routes
@app.route('/')
def index():
    # Track session activity
    update_session_activity()
    
    products = Product.query.limit(12).all()
    
    # Gửi event page view
    if current_user.is_authenticated:
        send_user_event(current_user.id, 'page_view', {'page': 'home'})
    
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Kiểm tra user đã tồn tại
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email đã được sử dụng')
            return render_template('register.html')
        
        # Tạo user mới
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Đăng ký thành công!')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Generate NEW session_id for this login to count as new session
            session['session_id'] = str(uuid.uuid4())
            send_user_event(user.id, 'login', {'username': username})
            # Update session immediately after login
            update_session_activity()
            return redirect(url_for('index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    send_user_event(current_user.id, 'logout', {})
    logout_user()
    return redirect(url_for('index'))

@app.route('/search')
def search():
    # Track session activity
    update_session_activity()
    
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    
    # Base query
    products_query = Product.query
    
    # Filter by search query
    if query:
        products_query = products_query.filter(
            Product.name.ilike(f'%{query}%') | 
            Product.description.ilike(f'%{query}%')
        )
    
    # Filter by category
    if category:
        products_query = products_query.filter(Product.category == category)
    
    products = products_query.all()
    
    # Gửi event search
    if current_user.is_authenticated:
        search_data = {
            'query': query,
            'category': category,
            'results_count': len(products)
        }
        send_user_event(current_user.id, 'search', search_data)
    
    return render_template('search_results.html', 
                         products=products, 
                         query=query, 
                         category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    # Track session activity
    update_session_activity()
    
    product = Product.query.get_or_404(product_id)
    
    # Gửi event product view
    if current_user.is_authenticated:
        send_user_event(current_user.id, 'product_view', {
            'product_id': product_id,
            'product_name': product.name,
            'category': product.category,
            'price': product.price
        })
        
        # Lưu vào database
        interaction = UserInteraction(
            user_id=current_user.id,
            product_id=product_id,
            interaction_type='view',
            details={'product_name': product.name, 'category': product.category}
        )
        db.session.add(interaction)
        db.session.commit()
    
    return render_template('product_detail.html', product=product)

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Track tab activity with unique tab_id from JavaScript"""
    data = request.get_json()
    tab_id = data.get('tab_id')
    
    if tab_id:
        user_id = current_user.id if current_user.is_authenticated else None
        
        try:
            from sqlalchemy import text
            # Use tab_id as session_id for unique tracking
            query = text("""
                INSERT INTO active_session (session_id, user_id, last_activity)
                VALUES (:session_id, :user_id, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) 
                DO UPDATE SET last_activity = CURRENT_TIMESTAMP, user_id = :user_id
            """)
            db.session.execute(query, {'session_id': tab_id, 'user_id': user_id})
            db.session.commit()
            return jsonify({'status': 'ok', 'tab_id': tab_id})
        except Exception as e:
            print(f"Heartbeat error: {e}")
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return jsonify({'status': 'error', 'message': 'No tab_id'}), 400

@app.route('/api/track_click', methods=['POST'])
def track_click():
    data = request.get_json()
    
    if current_user.is_authenticated:
        event_type = data.get('event_type', 'click')
        event_data = data.get('data', {})
        
        # Determine interaction type based on event
        interaction_type = 'click'  # Default
        
        if event_type in ['product_card_click', 'product_link_click', 'recommendation_click', 'action_button_click']:
            interaction_type = 'click'
        elif event_type in ['product_view', 'page_load']:
            interaction_type = 'view'
        elif event_type == 'search_submit':
            interaction_type = 'search'
        else:
            interaction_type = 'other'
        
        # Send to Kafka
        kafka_event_data = {
            'event_type': event_type,
            'interaction_type': interaction_type,
            **event_data
        }
        send_user_event(current_user.id, interaction_type, kafka_event_data)
        
        # Lưu vào database cho product interactions
        product_id = event_data.get('product_id') or data.get('product_id')
        if product_id and interaction_type in ['click', 'view']:
            try:
                interaction = UserInteraction(
                    user_id=current_user.id,
                    product_id=int(product_id),
                    interaction_type=interaction_type,
                    details=kafka_event_data
                )
                db.session.add(interaction)
                db.session.commit()
                print(f"✅ Saved {interaction_type} interaction: User {current_user.id} -> Product {product_id}")
            except Exception as e:
                print(f"❌ Error saving interaction: {e}")
                db.session.rollback()
    
    return jsonify({'status': 'success'})

@app.route('/demo-no-data')
def demo_no_data():
    """Demo recommendations cho user không có dữ liệu"""
    recommendations = []
    analysis_data = {}
    
    # Simulate user ID 999 (user mới không có data)
    demo_user_id = 999
    print(f"🎭 Demo NO DATA recommendations for user ID: {demo_user_id}")
    
    # Try API server
    api_result = call_recommendation_api('recommendations', demo_user_id, num_recs=6)
    
    if api_result:
        analysis_data = api_result.get('analysis', {})
        recommendations_data = api_result.get('recommendations', [])
        
        if recommendations_data:
            product_ids = [p['id'] for p in recommendations_data]
            recommendations = Product.query.filter(Product.id.in_(product_ids)).all()
    
    print(f"🎭 Demo NO DATA final strategy: {analysis_data.get('strategy_used', 'unknown')}")
    print(f"📦 Demo NO DATA recommendations count: {len(recommendations)}")
    
    return render_template('recommendations.html', 
                         products=recommendations, 
                         analysis=analysis_data,
                         demo_mode=True,
                         demo_type='no_data')

@app.route('/demo-recommendations')
def demo_recommendations():
    """Demo recommendations không cần login"""
    recommendations = []
    analysis_data = {}
    
    # Simulate user ID 1 for demo
    demo_user_id = 1
    print(f"🎭 Demo recommendations for user ID: {demo_user_id}")
    
    # Try API server
    api_result = call_recommendation_api('recommendations', demo_user_id, num_recs=6)
    
    if api_result and api_result.get('status') == 'success':
        # API server response
        recommendations_data = api_result.get('recommendations', [])
        if recommendations_data:
            product_ids = [p['id'] for p in recommendations_data]
            if product_ids:
                recommendations = Product.query.filter(Product.id.in_(product_ids)).all()
                
                # Sắp xếp lại theo thứ tự gợi ý
                recommendations_dict = {p.id: p for p in recommendations}
                recommendations = [recommendations_dict[pid] for pid in product_ids if pid in recommendations_dict]
                
                # Lưu thông tin phân tích để hiển thị
                analysis_data = api_result.get('analysis', {})
                
                print(f"✅ Demo API recommendations: {len(recommendations)} sản phẩm")
                print(f"📊 Demo Strategy: {analysis_data.get('strategy_used', 'unknown')}")
                print(f"🎯 Demo Total interactions: {analysis_data.get('total_interactions', 0)}")
    
    # NO FALLBACK - chỉ dựa vào Kafka behavior data
    if not recommendations:
        print("⚠️ Demo: Không có dữ liệu Kafka")
        analysis_data = {
            'strategy_used': 'no_kafka_data',
            'note': 'Demo: Không có dữ liệu hành vi từ Kafka. Trong thực tế, hãy tương tác với sản phẩm!'
        }
    
    print(f"🎭 Demo final strategy: {analysis_data.get('strategy_used', 'unknown')}")
    
    return render_template('recommendations.html', 
                         products=recommendations, 
                         analysis=analysis_data,
                         demo_mode=True)

@app.route('/recommendations')
@login_required
def recommendations():
    # Lấy gợi ý từ Kafka-based recommendation engine
    recommendations = []
    analysis_data = {}
    
    print(f"🔍 Getting recommendations for user ID: {current_user.id}")
    
    # Try API server first
    api_result = call_recommendation_api('recommendations', current_user.id, num_recs=10)  # 8 cùng danh mục + 2 liên quan
    print(f"🔍 API result: {api_result}")
    
    if api_result and api_result.get('status') == 'success':
        # API server response
        recommendations_data = api_result.get('recommendations', [])
        if recommendations_data:
            product_ids = [p['id'] for p in recommendations_data]
            if product_ids:
                recommendations = Product.query.filter(Product.id.in_(product_ids)).all()
                
                # Sắp xếp lại theo thứ tự gợi ý
                recommendations_dict = {p.id: p for p in recommendations}
                recommendations = [recommendations_dict[pid] for pid in product_ids if pid in recommendations_dict]
                
                # Lưu thông tin phân tích để hiển thị
                analysis_data = api_result.get('analysis', {})
                
                print(f"✅ API recommendations: {len(recommendations)} sản phẩm")
                print(f"📊 Strategy: {analysis_data.get('strategy_used', 'unknown')}")
                print(f"🎯 Total interactions: {analysis_data.get('total_interactions', 0)}")
    
    # Fallback: try direct engine if available
    elif recommendation_engine:
        try:
            print("🔄 Trying direct recommendation engine...")
            result = recommendation_engine.get_recommendations_for_user(current_user.id, 10)  # 8 + 2
            if result['status'] == 'success' and result['recommendations']:
                recommendations = result['recommendations']
                analysis_data = result.get('analysis', {})
                print(f"✅ Direct engine recommendations: {len(recommendations)} sản phẩm")
                print(f"🔍 DEBUG - Strategy: {analysis_data.get('strategy_used')}")
                print(f"🔍 DEBUG - Latest click product: {analysis_data.get('latest_click_product')}")
                
                # IMPORTANT: Ensure product objects have priority and reason attributes
                for i, rec in enumerate(recommendations):
                    if isinstance(rec, dict):
                        # Convert dict to Product-like object with additional attributes
                        product = Product.query.get(rec['id'])
                        if product:
                            product.priority = rec.get('priority', 'unknown')
                            product.reason = rec.get('reason', 'No reason provided')
                            recommendations[i] = product
                        print(f"🔍 Product {i+1}: {rec.get('name')} - Priority: {rec.get('priority')} - Reason: {rec.get('reason')}")
                    
        except Exception as e:
            print(f"❌ Lỗi direct recommendation engine: {e}")
    
    # ✅ NO FALLBACK - Chỉ dựa vào dữ liệu thật từ database
    if not recommendations:
        print("⚠️ User chưa có tương tác - không có gợi ý")
        analysis_data = {
            'strategy_used': 'no_interaction_data',
            'note': '✅ 100% dữ liệu thật: Chưa có tương tác. Hãy click vào sản phẩm để nhận gợi ý!'
        }
    
    # Debug log
    print(f"🎯 Final strategy: {analysis_data.get('strategy_used', 'unknown')}")
    print(f"📦 Recommendations count: {len(recommendations)}")
    
    # Gửi event xem trang recommendations
    send_user_event(current_user.id, 'recommendations_view', {
        'recommendation_count': len(recommendations),
        'strategy_used': analysis_data.get('strategy_used', 'unknown'),
        'has_behavior_data': analysis_data.get('total_interactions', 0) > 0,
        'api_used': 'server' if api_result else ('direct' if recommendation_engine else 'none')
    })
    
    return render_template('recommendations.html', 
                         products=recommendations, 
                         analysis=analysis_data)

@app.route('/category/<category>')
def category_products(category):
    # Track session activity
    update_session_activity()
    
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Hiển thị 12 sản phẩm mỗi trang
    
    products = Product.query.filter_by(category=category)\
                          .paginate(page=page, per_page=per_page, error_out=False)
    
    # Track category view event
    if current_user.is_authenticated:
        event_data = {
            'user_id': current_user.id,
            'event_type': 'category_view',
            'category': category,
            'timestamp': datetime.utcnow().isoformat()
        }
        send_to_kafka('user_events', event_data)
    
    return render_template('category_products.html', 
                         products=products, 
                         category=category)

@app.route('/categories')
def categories():
    # Track session activity
    update_session_activity()
    
    # Lấy danh sách tất cả danh mục và số lượng sản phẩm
    categories_data = db.session.query(
        Product.category, 
        db.func.count(Product.id).label('count')
    ).group_by(Product.category).all()
    
    return render_template('categories.html', categories=categories_data)

# Import recommendation API
import sys
import os

# ✅ Use REAL DATA API server only
RECOMMENDATION_API_URL = os.getenv('RECOMMENDATION_API_URL', 'http://localhost:5001')  # Real data API

def call_recommendation_api(endpoint, user_id=None, **kwargs):
    """Call recommendation API server or fallback to simple recommendations"""
    try:
        if user_id:
            url = f"{RECOMMENDATION_API_URL}/{endpoint}/{user_id}"
        else:
            url = f"{RECOMMENDATION_API_URL}/{endpoint}"
        
        print(f"🌐 Calling API: {url}")
        response = requests.get(url, params=kwargs, timeout=2)
        response.raise_for_status()
        result = response.json()
        print(f"� API response data: {result}")
        return result
    except Exception as e:
        print(f"❌ API not available, using fallback: {e}")
        # Fallback to simple recommendations
        return get_simple_recommendations(user_id, kwargs.get('num_recs', 6))

def get_simple_recommendations(user_id, num_recs=6):
    """✅ NO MORE RANDOM - Return empty if no real data"""
    return {
        'status': 'success',
        'recommendations': [],
        'method': 'no_data',
        'note': 'Không có dữ liệu tương tác. Hãy click vào sản phẩm để nhận gợi ý!'
    }

# Fallback: try to import direct
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'recommendation-engine'))

try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'recommendation-engine'))
    from simple_recommendation import SimpleRecommendationEngine
    recommendation_engine = SimpleRecommendationEngine()
    print("✅ Simple Recommendation Engine loaded successfully")
except Exception as e:
    print(f"❌ Failed to load Simple Recommendation Engine: {e}")
    recommendation_engine = None

# Khởi tạo database
def create_tables():
    db.create_all()
    
    # ✅ Tạo dữ liệu sản phẩm THẬT nếu chưa có (chỉ chạy lần đầu)
    if Product.query.count() == 0:
        sample_products = [
            # Thực phẩm tươi sống (15 sản phẩm)
            Product(name='Gạo ST25 túi 5kg', description='Gạo thơm ngon, chất lượng cao từ An Giang', price=180000, category='Thực phẩm tươi sống', image_url='https://tse3.mm.bing.net/th/id/OIP.tiXbm0NPSwS5vHgDN13s9wHaHa?pid=Api&P=0&h=180', stock=100),
            Product(name='Thịt heo ba chỉ 1kg', description='Thịt heo tươi ngon, đảm bảo vệ sinh an toàn thực phẩm', price=180000, category='Thực phẩm tươi sống', image_url='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxMTEhUUEhMVFhMXFxgWFhgYFxYYGBgaFRcdFxoYFRsYHSggGholGxgVIjEhJSkrLi4uHR8zODMtNygtLisBCgoKDg0OGhAQGzUlHyUtLS0rLSstLS0vLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tN//AABEIAOEA4QMBIgACEQEDEQH/xAAbAAEAAwADAQAAAAAAAAAAAAAABAUGAQIDB//EADsQAAEDAgQDBgMHAwMFAAAAAAEAAhEDIQQFEjFBUWEGInGBkaETMrEUUmLB0eHwFSNCBzPxFkNygpL/xAAaAQEAAwEBAQAAAAAAAAAAAAAAAQIDBAUG/8QAJxEAAgIBBAEDBQEBAAAAAAAAAAECEQMEEiExQRMiUTJhcYGRFBX/2gAMAwEAAhEDEQA/APuKIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIi6PeBuUB3RdBUC51IDsiBEAREQBERAEREAREQBERAEREAREQBERAEREARcFRsTjWsF1DdEpN8IkleFbFNb8xAVZ/U3OJAVM6hV1kuOppsWkfnv7LOWT4OnHpr+p0ad+YsAkSVGq5qdgPVUGHe8gyG2sAPYbc16irDZMbwLzPD9U3tm3+aKZaf1Nx4x5LscfxIB8VADX7N3tHdmOpVhQpgXqRq5AqeSkowXg7NzEcYXduJHD0Xi+jRdv9UZSYxjnEyOHRLKOMfCJDcVp8P5x4KXSxLTxWYfnlLSC6/nc+Ch1O0VMGGg8D6qvqxRqtFOXSNyCuVl8hz8Va3wySDBgHmL/qtOFpGSkrRy5sUsUtsjlERWMgiIgCIiAIiIAiIgCIiAIiIAur3gCTZcVKgAkmAsb2mz0ghoi8mDwHXxuqylSNsGCWWW1FhmfaAB+hhEbE7nyUKritQECQTz5LONxDKtgWtfvafoSrPDYjUAx0B43E79R1O6w3N9nrf5o40qRKrFzSXMNuIPXly8lLp1SWy8QIkHw5qozF7mt7o1g7W7wPluPddsFmclrbyLOa7cR4/TwS6ZDxuUbRNp0gSe/4gbAle1PD07MLiYuCZ9OSgfEaZJADg65uNjBU7UGuu0mNuI25qUyk0y3qVm02TYKpxGNbBcSNPj7LnGu1DU+Gho5ghZLH4g1WnTYNPAWg7KuSbTLaXTKXLO2a9p9w3bgNlCw/aOo8lr3f2zYgdRG3JeNLIqj+9pJBP8KtcF2Z3LhpPDxWKUm7PVk9NjjRVUqxLXsMk7j/ANT+i7ua57GkDvNkePEFaJmUUmRqeJXoalBgtcn8rK6xvyYy1cb9qI3Z/Du+006pEXGr0gr6YFhMvxmqoxjWgS4D8yt0F0YlSZ4mvm5zTfwcoiLU4QiIgCIiAIiIAiIgC4ldK9UNBc4wBclZTFdqXl4FFg0zcnj+ipKaj2bYsE8v0o1r3ACSozsX90F3gs9XzOpWs0HTs4N385V3gGQ0dBF0UlLotLA4L3dmf7Q4vEGo1rQGt3BJiPI7lUeZ4KrILjTfq/yLhPvuFu8wwbKrCx7QQQYncGNxyKx9bsmJJa6o61hLRB8Y4qk4s7tLngkk+K+xEyrLQ6fitaWni03YT18twvbGYRzRDYIE6Hm5EXDX8xvfcKvNU0ZBa5vME6pAMeUKfgK0GG3HAG/1Wdro7JKTe67R45XmQqAcHA94Sd7iByOylYpzWu1cHRcjmIt1sV1rZU0nW0BrzxHHxPHzUimx5Gl0TG4F7frZSvgrJxu4/tHm6sT8tuQIMHnuvalUDQXuho9dv5K9MJROk6zaJPSP2VYKRxDzfTTZc+e6q38BKMm76R6RVxAcAIYQRHXgvbBtp4ZhBhz3WI4W4FdcTjSSG0rNDT09SvDC4fWCAZh0u/Yokl+SJSbjXSOxx1SRsNzHIDYKL8Rz7ucSTby4/kvbCs1P0sbMG5O3or5lBjGiAOisk2ZznGHFGebhXueTBvME+ilNydxg2EeannMG6i3iAJ85/RR8VmJIOjfqp2oo8s/HBMyrBCnUY4nZxPqIn3WxCwTM2dAgcirrB5w7TBG4tJV4NI482OcnuNIipmZseIUwZnTiS6PFX3I53ikvBNRQaWa0nGA8T5qW2oDsQpso4tdndFwFypICIiA6PqAbkAdVBxeb0mCdbSeQIJK+Tf8AUdau/WdZnUGibDSJIuImBPLZWtLEamzFzuYvPPl7LD1b6PX/AOU4/W/4T+0Wf1KoLRAZxa0y63A9PBVuVNeQIa4Ecx3T+YSllQPeM778h9Z2Vrg8Tp2BMcXbmFk027Z3LZihsxo0uV0gxgAFzc8TJ5qZpJ46R03VZhswbAMRa8dOK8cbmwLR8N13SPDnPVdCqjx5QnKZZ/HAkAmRuTeVQY7NWl0FxZexkAr1y7FjX3tiCDPXYlQsxyik1zSykXC7i7UBTv8Aedv1hVcuDfHjjGVSPZuY0yzS+n8QfjdqPuF5Uq1O4Y1rDwv+tvZZ/G5xQYCGUyHi3zmPFt1mKmdVNeprrjlafHmsJZD1MOhck31+T6KcaADqcLRO912GaUg4d6fcX6jgvnNTMa1ax2mYA47StJ2byUy2rWOlnAHcn9FClJvgtk0uPHG5P9GvoEGXPbpaB6+KqsbWDm6aYDWAjYbyN/Hgma5hrhrPk+p4KwwWAAaHHxHS1h9VrXhHnXs9z/hEpZX8RrZOlsbRc8rqc5lOiyLBo91xmOYMpM1Oe1jRu5xAHuvmme9uhUOiiHGmD3nukF3Rg3HifRW4iRCM8zrwbwZ1TB0MbLonSwFzoHRt0q08VWph1Onvs1ztB3i/JYnA9qtEaGMaXC7wwB3qLkeMq8wPbtwcJMidrLP1V5OmWhyrmKL3LuzuJ+esWtN5YzveBLjE+im0sobJiLG4JlT8szynXZLXDqJuF2r16LeQm/7rS49nBeW2muTh2XBrRAkchAXg9sH5beq7YbNGuNyHKxe9r2w0gdYmFPD6Ktzi6kitAJ2BC6mlFjbxsrEUXtA7xIC9Q0P3Psm0j1aKSANl2o4+Dv6KfjMIARpaXDjsBHpKg4ksBP8AZ90po1Uoz8F7gcXrbM+Ur0diiDt58FnMDiAHi2jzMe6n486XC8tN/DmpUrRzzwJSouftCKo+1fiCKbK+gfLcBlVOkQXP1PBnTqMAxsALT4qb9sJIaW6DO7XSR0N/yVZmOatYP7WkA8gI9VWMxzCdVweMbi288tlhL7H1Mccp+6RusO6ZDqgLDbjq4HlzC4pVHGBtBjbf06rJYTPbhpc7aBsTJOxtfxUmhnjtTmFzHDwMn0MNPRV3JGL00rZt6FRwAIMHrZRszzPQ0FzJBMOdbunh681RYHMnN7tMkgmdJMx0BjZQe1PaBopllSmfiRG5G4kEwbjlZWjku0jnelamrLXF5xTae64zPzA8ORavDtDmzvsTmNqt+I7v6eJZquR0sVhcr+JXeY+UCXE7ADeTbgvGninVKpeZvDAOTQIH88VFNvk63hhGq8ck37S6poAMnmfK19tlbZbkFar8rT1m31Xp2PyIuf8AFqWpUyHEnjFwB5wtdjM9eajG0xpB34n9uCKCorm1U09sDjLsppYVuqpDqlrDhF/qvWtXe52pw7o+Uc52H0UWhQc9xE983585k81fYbLGtALzJG/JaJfB5uTJTuTtnhluAsHPPMhvAKL2o7T0sLS1O7ziYYwfM4/k0cT/AMLp2n7Ssw7YgOqOnQwG5t8z+TfrwWBfnRqOL6zJfx5AdByRy28IrjxPK90uilzzGYjGu+JVMtF2sA7jAbGOZ6lRcHhHAgRqB4H3hbfAZrRgBzYmbRayvcNhaFQB50QNjAt5+iryzqtY/B8pwuGeYn+XVmzU3/ESRfnfiOS+kUOzFCZiwnY2Xljsiwj9qmg7HiJ6qHBs1x62K45MLhsW9lgfGbdVcUc8q0yBvSOkkOvE7wRsrHE9izANJ7Xx5Kqr5BVE6mmRcW35+SzcGjoWfFk7PoOEex1NlSkJkDeZAKi4PNmsc5vxWyNpkKs7GfFYS186AOPDw6Kfi+zlNzy8EiTJHibq+20mjznsjNxm7RPHaxjQ6CHRuZiejea9sJ2m+JENusVmuDDamlogN4kzPkr/ACSvSZTDdY1b/lw6qE5t1ZbJp8ChuSts1eHzJpvNuKlUqjXibEbKg1G4sWEXXm8kRpMAEGOnFaqUkcDwxfXBaYvKdYMEAjy8FWYzFkBrTFov429FYYbMw9j2uJ1AGZ4kXWXxtRzbR4eSiTpWjXTwlJ1PwWn2x/4fQovT4J+6izs24PkGb0XU3OZwPeb5ibeSqKL3AyATI/b6rX5pQD26hJLYH4hpFx13XY4+nQpl1Jga557rQZi0Oeekgx4qfpR7HqNpUVuWdn61W726G73s6BvbfzXFDAVjU+G2k+ZtYx4zsfFTKGKqVXMbLiSZdHUwPafVb2viG4SgHVDDG/8A1J2b6qqW5mWbUyxcdtkPB4KngqBqVnNDgJJ5dG9Z918uz7M6mIfreZJJDRF4mwsrztl2rZim02NkNBLnA2J4NB6b+yj5FlzPhfHdOoO0sbvqfFj4DdbUorg5Mbk25T7ZVYwupn4LbGG/Ei0mBDXdBx5k9FoOxWTGtWDiJa0y4n2HipeX9iKhdqrODWTJdO4/XxWooPawClh2wwAzzdb5nFQTky8NR7J2NxIcTSaNLGgg2ETIjyVN8KHkg3NgRw5/oveiHPMQYJ9Z4rQYLLGsu6Cd+gUq5HI5rEjplGCNJoLok3PPwVZ2j7U08PLS4OqbtpjcWsXngOPNe+d5oWAtae8dvwjgfFfL8dkEuc5tR2omTq70k8yblS+OiMWFze+RGxLX1nOqVKhdUcZLj7ADgBwC60sPVFgZi4uvKpgazNu94H8iuKGZFsa2kHjwWdNnVaX2LSnUJaC9hkEt5dfzKtsKGn/u6WzcEGfQbqFlWbsdZxAvxWjwuBovggC3IqFFkvIqOcOa0xqOnVMzbz9rdV4VaQ5jU6/S24nmrrC4FgESZiP+V70cAzTpdBN7xzVtrMHlSdopssfVovL92cgQZWroZvSdHeAJEwbbqs/ppbOgzbY8T1UHEU3wPiNO8SAJ391KuJSShkdmsYWOHdIIPIghHD0WNdTdSbqa5wBIgttJAMgjgrKjn75FgWkXkwWnx4jZXUkZy08u4uzv2jwlg7SSIAMb+ay/xDDi0ctAkCLnnyK2eDzhlRrdY0udNiZFjG6j1Mjo1DqabcQDYhUlG3aN8OdwW2aM5gsfUpglj9xee83bh5q5y/tE14/vANP3v8THuN16jLKDjEbGNzwt+qqM3yv4Z7oJYevPgfNRUkaXiyOmqZsGUg4QOP0XbE0m0mNc8S4Elv4nGQAslgcyqUtMGWgAEG+/L+cloKld1YsLgAG7cd+Kb4v8nPPDOD74IH2iv95Fcf0j8XsiimT6uP4MZWpAhz2NImdTeRgzPlfzWWzWkTVLx8p+XoOA9Fs8SKlB5D26XRDmuFnD8x1Coq1Gk6rq1ANNzMAtAG3UxsVlOz1NNkXZYZY2nhcK7EugvIOieewHj1WJzvPa+Id/cedNu6LNEcY5qRnWYOrOgyKTZ0N5AWnxKm9luyb8SWuqDTT+t+C3hSVGGWNNzkQezORuxdZpghgMudG3S/HovrGCyFrCwBo0NB3udRIv6KRh8NRwtMNbDQBtxKrsTnhIJ2by42/WytS8nE8k8j9vR65tj2ucGD5G/MVV05qvDGjS3kOogknjYlV9WqXmGzfccP5+q1uR4AUmS/5j7dPFQvcy00sUfuSsFhgxsBR84x+htoM243PlyUXMc8DXFjAHOG87DpbcqpFJ9Uy6ST/IHIK/2RjDE290yFiKrnkk3JXiMKStNgsgc7gr/B9mwNwpWN+TWeqhDhGGw2Sl3BWlLsix4h7JHULfYfKWN4KaygBwWijFHDk10n0fMz/pbhXXAew/gcQPQyF44z/T3EUu9hapeRHcfDSY/ELey+rBqQjSfgyWryI+Mh2LoT8ejVbPEtLmjzbIhTsBntN8Alp5nkvq5aFX4rI8PUu+hTceels+sSq0aLWJ/Uv4Yg5hLSWfM3gf8hyB6qRRxrXgQeW+4kcVcYzsRh3Xpl9M8IdqHo5UeN7LYundhbViYg6SeUg291G00jlxS80SNDSCIBHL+eajnLKcEAETv+yp8RUrUz/cD6W06mkCxk32vspVHOxwv4fXwUNGyjKvaznM8ra1g0SHA+pMehsqtlCpTa5twfmgHlbh4hW9LG63bt0HmL9IU5rhY7yqONmiyOKp8mUZVqMeHA3kBw4Hx8lo8txRqt74AO3j/AvSpl9NxJIvb2UVuXub8sHlFv5ZVpomWSM18MlPyKm4zcK2yrLAwC8gKnoVqjADBI5H81fZZiy8Huwdj+yJRbMMssm3vgm/ECLtpbzHqi1pHJyZPtC8VXj4l23B6T+8LEZplNRuo6ZaNiCJjw4reY6hKz+LDqZBABAOx26xyWeXFyepp8rilRQdmcmbiaok90CSOcLfYjHMojTTAJFugWVy2lprCvQJDS6Krdi2bXA4X3VrisHUqOLWghvE8LLOFxVeTXUSWWacuiLjsbqBc4lz/bfb2co+Ay59cmIAF+glXmF7ONBGs6gBYc+pVjUr0qLYAAnYDiVptfbMHnSW2HZ0wOXU6ALtzF3EewUDNM0cXfDpfPz+7PHxXtRpYjEmKTYGxeflH/jPzHqtRkfZenQEnvPNyTzKsot9dHNPLGDubtmcyTso50F1gtdgskpsG0qzDV2WqSXRxZdTPI+WebKQGwC7rlFJgEREAREQBERAcJC5RAdHMB3Eqox/ZfCVfmoMB+80aHerYKukUVZZSa6ZicV2Fi9Cs4chUGr0Ig+sqixmW4vDDv0i6nN3MOoCeMb+y+prghKN4aua75PkuFziZgzHkbdCrOljA6D0lbnGZRQq/wC5SY48y0T67qkxXYmib0nvpnodQ9HXjzSkbLU432qK6jiR4hXOWd6zbKiqdksSyA1zHtBkXLD5i491o8gyt1Ml9SQ8jTp1SAJnwna6pTsjNKG24sk/0en19SiskWhx7mZXF4VUmLwsrb18HKh1MpngrtJnTjz0fO3YY0362C/EcHDkVeU8xaQC0tFtjYg9QtEezjTvZSsN2eosMluo9f0WDhzwbT1UGuTKhuJq/wCzTn8Rs31P7qzyXshHfxTviPN9IJ0Dpe5+i1jWrsrbUc0tRJqlwdKdMNEAAAbAbLuiKxzhERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREB//Z', stock=30),
            Product(name='Thịt bò úc 500g', description='Thịt bò nhập khẩu từ Úc, thịt thăn mềm ngon', price=350000, category='Thực phẩm tươi sống', image_url='data:image/jpeg;base64,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', stock=25),
            Product(name='Cá hồi Na Uy 1kg', description='Cá hồi tươi ngon nhập khẩu từ Na Uy', price=450000, category='Thực phẩm tươi sống', image_url='data:image/jpeg;base64,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', stock=20),
            Product(name='Tôm sú 500g', description='Tôm sú tươi ngon từ vùng nuôi sạch Cần Thơ', price=280000, category='Thực phẩm tươi sống', image_url='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxMTEhUTExMWFhUXGR0bGBgYFxgZIBogGBobFxsbGBsdICggGB4nHRgYIjEhJikrLi4uGB8zODMsNygtLisBCgoKDg0OGxAQGzImICUtLS0tLi0tLS0tKy0tLS0tLS01LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAOEA4QMBIgACEQEDEQH/xAAbAAACAwEBAQAAAAAAAAAAAAAEBQIDBgABB//EAEQQAAECAwYEAwUFBgMIAwAAAAECEQADIQQFEjFBUSJhcYETMpEGQqGx8BRSwdHhI2JygpLxFVPCBzM0orKz0tMWVGP/xAAaAQACAwEBAAAAAAAAAAAAAAACAwEEBQAG/8QANBEAAQQBAwEGBQIGAwEAAAAAAQACAxEhBBIxQRMiMlFhgRRScZGh0eEzU2KxwfAjQvEV/9oADAMBAAIRAxEAPwB9M9qErtHhYMCQooDjixOzqOTEhm0eCbzumz2laFzQcSQxamIO4BOdK5bxPwZKpvjBAMwgcWY2cDJ2o/KJuAopxB0tiAI4XycaRstZQp3svNPmO7dCKxRV6k4WYMnIDZoTe0N9Tpc2VIQlKUrKTiZ8fExSScg7O1aiojyZZZptRKkqmJIeWtz+zH3R7rVKSnWhFYsva2ASVqwpKkIWpBIBwnCah8jA2ZLaMEJrGNgcHnIdj3/dWfZETbMJS9grFhqFHiKmOTkn1MWSAiUgISScIAxKNTrXTU9mhVe96EKLFyCBQ6ktX4U5wHbLYpcxSZZU4IZI96jDmQ5SW5xJkjYbPRM7CWRlXQNmvdO7zvYSkBS8VaAAO+v08Qt1oUmQqZLLkJCgQHpQkgGnlcxG3WdMxARMdNQaM4I9RqRHqLQmUyZZLAMHLmnOLQa44AwqTXRso9Qcqu47SpcsKWFByaqDYhmFDcMc+UQu66jIK1Yk4TkA70LgmgZg9K5xTaL2xrwk8X0YBvC3rQoJORDv3rSCLWtAc48JnaPO4NGCm86yyFzEzl4saGZiwOEuHDVrE7RPkrA8VAWBUPpCS9SoJBSW0MeqtLCWRnn/AMtfnEPEY3DrVo4myOc2z/4nBvGWaMMLMUKAIYhgDoQRo0Ui8k+WUlKEp+6AAKuWAYCpNd9NYyNqtpoCWClu/UMAOxPwhpdigApnwlZwlQYlNGP1zhOnla5wYRZrlWNTptoLgaBPCfItkvRKQSXJASCo7lhnnFhRKmYVqlBRluQahsi5Yh8hm8Zu65SklZUkjqGd3LjfL4x1ptuELT+8hxyISfmImWRgjDg3qoghe6TxHhaO0LlzsctalBJABILHN/wL7vFFlkBCF2eWp8BSuWTzAUkq5eKhfaM19uUUpUg1WpR9GH5wdbLT4ZSpyfdPN6j0I/5jBNMbxuUObIw7Bx0+oTn2dlLRIdanK1YhV2BAzrQu7j8Yhdl5rmLmJwgISCQp60IABGpNTozawuRbDKLnI8aa6Eur0UQqv3+UGWu/BhcAEqIB05jFrkDHUABR4XHc4u3Nu8D0TOz2/BMw4uJqc9+uQgqdOE0KQolIUkpJGYxBnEZ+5ZwmqM4q8hUkJPOgL9HHWLJltUZyUIS5dlO+Rriy0A+MDvaW7nDrQQO0xDw2M5As+SZ3JdqbKhfGFrWQ6gCKJfCGc7k9+UV3TfxmT1SPCBRUiYFEEYRUkZEEsBlmM48VNwqAd/0rBMibLSVKShKVr8xSGxa10ep66xL4TQASmzAlzpR0oeSO8Qu20B3dcsqVOmWjGpalOUhXu4qqcvxHQFgwfPOBUzZxtCEodKAHmFSCQoHNlZbANV30yNd1ECusBtDyfRdT4GjafEOFyL+s4tH2aaSlawkpX7oKvKg6gkMXy4hBk6cUuAXhdJu6zid9owtMrTTEzYurdtc4n/islM0JmkjFqGZOxXVwD+uUAAW2XcKXsZJtbDzWUSyvox7Bv2EffT6x5Bdq3zQfCS/KkyWC3CurZPq416ivOIGwYFFYVQu4YOX6nfnpFqkoxKNQMxzJ25RQEF6u0C2F0uZRRBxSIz9l3Ysgjr0UTbj5eIfyqPxSCPjCy2rBxpJDTEqSa5FQKXhvb0plpClKSn7rkAq5DVR5VgD/ABdKgwlzFPQkowsNzjwluYByMBJIZG7ozRByCn6eIROLXtsHqkFstIWFrTQKSJnchCj3cGBJ85SME0OFpwsrofoEbDtDCz2LimIAfhWlu6kj8PWF00pEtYUphiB4ia0OLDmQMsqDWM98q2mx5Tmz24zlKwqDBmdzmHL7fVI7xfDX+04S1K4n/hA4j6QkuaYlK1oC1S3zWQCQU6GowCpDgu7MYcJtBSkoTKQoKNSkkFRehqCSXapU7tF6B8srbaao+ePsqE7Io3U8XY9/urVWbGvxEobUlSgnIN5U4nfqO0VzcK/95gpkyVhsv3y+UDonLSCkpWCksUtiJ2LJd8wO+gyGTMSpWZbFUKoc6gjQ0NIax+nohxJJyRx+gSnsmGWtAHnz+qPXbgCxwKHNKj/qaIzpoIKinDQs1RtkWwh2yJyj2fYE48OIIcDPeoHyiq9DhQQWfbarmK82qY9o2Y97VjSxPB3P9sAJDeFlJDY+AAHEHKQdArVLgJzA5QdZrYfDRs1Oxb8IzluUtE3GklKlM2HoKQ3uy1oWGICVEZpHDq7pHl6pHbWFaTUmN1+afqoRI2k2nW5TAEQJMnYvFOwl+gw/gYIt6hw0anKvRqEQKhQxrGik4e+AD5iH6nVSPibuHKr6SENeUPKt2CSpBGIoW7OQ4Ox0Lkl4by1yrQh8Sh1AfmCPxEIrwnK4RMQyVUlrA7MdyC5Y1qDk0QsAKCXOEpoquWSgSNAR72VYrMnrpjqPP91bkiDsH29E8tKVzElCRiUioqHUmoGznQ8w8K7zmYMOEukhKknrQ/LLnB9qxAJmIBChofQh/uqbsQNg6e8JgWAwoSojkT50nuAepVFiUxyNMjT5eyrxB7HbCP3Ta67QETFKFAsZfwnhbsTDBV4n7RLmBQICMKg4DAk151IPYwmsgxSpeBzMTkAQDmxAfQDCWzJxQmM0qNFOFVDAP0Ipy684XHq3BgZXBRv0jC8yeYpb+3XfNnFC0KSU9WKXPm5hmyrSD7fOTLDjINX6z1MZj2fvokBBYYUgA6lqV+EaOV4awCtyQXzoeojTZ3mmWPJP4WPK0scI5OB+UXLtqm5aQNNsk9c6WUEpTU+ID5SPM/NmABzcjdo260+8QSH0+JeCTMUij/WxG8S8MluNpyOUtm6H/krHRG2jiWwrv9CB/wDDLOuaictPGjSjKKRwlQapFNRkHeKJthVMUg4gEipL1BBzbfJjBM8uotXflAACQljhgdVPeiAkYe8eiZ/4gNxHQqwDaOhnYsSfiJvNUz56UNidj5QA5J2AzP4awUtE2bLJV+zTRkJUCsADMqAYHIMl2rxGCLvlygkuHUoMpRqVcidBsAwEAzJhDpBppFZ8TtS6nW3bwrUczNKLZ3t3NqmTLTLcISASOJQqpX8Si6ldyY8t1kVK8Ja2wzCKbZKDn594ZGW8tJyagO2wV+6aV0PJ4X31aMcgyiOJKwQ+YYsoHsSe0Klle+MtYMt8Q8/2KsQwtZKHPOHcHy9PqElvcYZvCrDjUylBiRQMBonN3bWF9gswxzErKi8tQSaE4mZOelRBF6THmpOikpV9f0x5Y7UFzKAhRzqSThS4w514WjFLs4W/sICSWcFKk4nd1JL1q5y5cRpyMPUWezqrLSEEZhBUhin3hhILGhzoXGjwlmJmkqxDhfEggg0SooVzHmeu0G2NayVolo4iy0pBAxYnKnfOr9IdHJsdZFjySZIg9tXXqm1ulgKSuXNmZAkLIXUUbEoFZow80LLWhaZirQkBaVeeWU0LAPi3yd2GfeKrLeqC4WSkgdKjMKTmO2UGTLUEoWaUb3mKnoAkNUhWEviFCaQ2bsnMDogcc3ykwdpG/ZKeeK4+/qgiUkiYhJTLBDMwwqIxAEPs42ME3jbDMSFKlEoUzGodgNi5DhQfl2iuVYXIl4RjWtIUt3cYVKBSeYc9uUaCbZUidSUyQoIBxOA5JAI6V1HqIqWXZVzaG4WEvmWUoQtWaVDh1HXqAYAkrKGVkx/6g/eH/tXNxLcIQlLMMJfxGGErbQMA3V9YS2iaDKSSXWFgE8gKU7Z9Ia11IHNtaALScICZhSoBQxJrUkOnCVahueoyMXSrsUohUshaSUqfJhTN+vwhLZZ6hJUpJLymNNA9FDor5iGt1JmEIlgghctzVgySQK6ME0jpJHEVaGKIAk0rFWUmWuUscKnCd3GRHfDCC2zBjQpCiFYACciCAwPItT+WNNZLOgEGZNo9KHQZKcUFANdYT3hZZYnzCBWYuY5fIhZKVjZNSCP3TuIWxya9qsuu8VTmlrABHC/lSaMxbIlgH5DaKL8GBkijMTpiwlsbZCYkcKvvCuggWyzWmmWpIqTXLTExGvLIu1Y0M+zCdKGNioHCVA6jyrB0cUPNI3juCu27gk9mQUKw4gclJI+XeJ3xZRMCZiQ1QF50fInXcbxTdAW4wsSn7xAZq5nXOHJtCUowUWpYAJ2UV5DKgS46mCDiCoLUhBBJWxAVUci511BKVdn2jU3XazNRiA4nLgfVIDtkocUtIGHhws+g/s53rAtzW0SrRxO0xktsVEadR84twzvjdbOVS1MDZGUVsrHbWDEA7OMosUlRIOF8X1TY84HRIVMdSQwGX73T6zicq2LAwuWOkbDgJgRGadY3UsMExkFwsdFMqKSzwSmwuELCmapPzj37EWBoX824f8PnAhmKHCDEHZqgWi+6c+tKO9Ad2M/hMsSfox0UfYf/ANR/T+sdE7Wev5Rb5fT8Lra2I4TTVo9siEkVrHWRgoE9esXXokD9olnJqN+fWFyniAXnhw8wlxjmU19EDbgpJIxqS4amEgg7gj8opmIMySSzqSGKsnDMPw6Cr0L1LJmkgqZ9TFlgkTEGZLmFK0mWVJKXS+HiNXLHDiH80UtYxkIG3x9SMX5rT0Uz5TtflnQHkHolM80lLNFplnhOhCm7VBgS1+IAlaSApeSq8JcA6aP8YOmniS6S6UJBUT5mycaGhi+y2YqlTMKUrUkgpBOqs+tBkdRGPytsuSabMQgpD4kpK0HYpLPUbnFSF06f4c8FEyuEJSpyA+ED0qRTrB15WJUoVBKKB9iUhRBGlSYztiKphMtKSqYVcAGZZwodwx7GGMFkB3CBxIGEwm3lMCsSpdnUrVXhpUT1JDwRZrYqeqWCiWEB3wICKM1KB220cHmM+lblxV8q7xvrvkIlWaXMoXQVKPVT4Sd28JJ6Q/UxxxkbCUMD3PFPRNyoQZxIS6ZSAhVW4/IVfygp9YcXoAiQWIoxJfXIqfkov0DRnvZ5BTMUo5IrMJPmxJxn4sj0iyffMzHjUcQ1SdQcxFYPDeU1wJKUe1spJKVJxOEhwrYjFQM4Zw5Lh1NRjGQIHiJBLJKkudg+fzjde0K0z0JmpJcApUNmqBnk1XHetBh7wls8TeVFYTC5poRMBXSWp0rpRSScBYvzBPflGssl18MqWT5SuWS+gUkpJPNKnjGXVeCcQlLB8JacC9WcVWnYpNR05tGySkSliXiJyJcksoI8IgE6HACOShvAuvqmADbhe2mwEJUhmWh3b3hqW1UM+aQfu1RXjZ8JwgH9mlNTm6xjOIbupjXSNOZ7qCiqoILs7MQoFtWNWhdedklKUwZiVlJQcnCeFTiqUkBqBxkxBgWoSsVaZx76fy5fCnaNZdtqQtOFJIdJxAmhq5Kejv2PKMpeEggmlfyiN2WwpmIw1IUA2+hHQgt3iwxrXtIPsllxY8ELRzJLLZSWJr3BUlTcnD94JmSAqYhTJTnjxUSCgYiWGhSxbUvEbfwzpag5SoHPcYf9BQTzJgr9nMKkTOFKgK7KGp9awoFMk5RlgUFy0z0rSFBCgXwghUpsGeQCRLqKcLaxm1WYt43CMC08ApwhuIfLeijoYOFnCUky1OhLIU5AckqUlWF8ixb+CCfaW60ps9mnS1lSVApVRsMxDcJGnBgA3wvqIex3FJDgtFZb1T4SUoroG+DQVOu1Ql4yeLVOz7bneMh7OqMtCVODVwRXzOa7EKCgRuk6MTrhbTOZCe/LmY2W20NkjoN5csKStzmPyeiqlWtRGDt9fH1gqbZ0+GCzK33gW3WXwyGL0eCLJimOS5CW1zh0jwWiZrqaMn1VdjSCYyLJ/CDxneOhv4Y/yh6GOhf/ANWL5T9kXwLvMI1EyUuWEqYYR9HrGctU05E0yg28ZeEDDR8wPnA13zmcKArm47emcTCBHGZWA56FBIS9wY7p1UV2d04ksCBWudK9DErBNKnJIASwc83z7CKrzAQeE0Iy26R1zKfETlUnsGirqAfhi45vi+R5q3pK+IaEhtdpxFSnqSBnsB+fwMTs1vmS8RBZwx1+iNDzgCbMR4ZIPF4ymFfIQnC5yNQfU7xyZ7gxgklegIR9qR4skrqSMy4eihm5fykV5NGNt8rAtxT9aGNFZLSpExxUKzBAIOxINCz/ABMKL5SHLBhmBtq3bLtDWlClcpI+vr4xsJEzxbMizlRxrmJrXymh/wBWua07RjEroOf5xuvZlSEspnKZQVnkEJJWWzzwjvDZRdKYMK1KGM0uwWtTcxixDtlSA7RkTHt1zCpCnzDHo7gt3b4R7biwio/lMtU2BLrKceHECA7MVMcIU+QJp3B0jOW5IxEQ3nGhOsKLxVmrlBtKhN/9nl3eJMWTVKVpJDPkMXyf0h3OsWFcgn7nhqJdtkKpUkJLP+6IR+wNsMqaFBuMKSd3QUu5bLDMB9ecaL2in0lrlqdKcG2YQahidRrHOOU1o7qoXiSSlVFJJB6ikUKUQXybNgCRzbX8oIvCaVTFLLDEcVHAL5kA1zeB1rq/rCjgoQo3zdyVpCwwJzAehDfAvn+DRk7PZMFrljIeInPqPnl3EbVbmWQlg7JVkHBqkkmlCGJOTS+cZK9jhWhR91QLjkXh0bkLwCFqr5SMCwGdCw9XoVLBKX34fSLfaGzJQpCknFjQCo/vgAkn+JKkKrXjeFlqGOS5qQH6sofgYsnTCpCSRXqSSaCpNdBSBJoKXhVG0lBxAAuClSTkQaEctwRUGsQmW0KSzqwpBUkEhwSUpYlmXQJLsKbNHBRIrmIBn50g430lOCIuicDMSkEALOE55mqT6jD3Eae7bb4ai0Yaclman1n2MaqynFJRNJ4leZOxBYj1Bja0ko8Dsg9Fj62KjvHK1Fkk+KMS1NSg+RPKKJNpMsnCSHoWgWxWxSgECm5/OCZsjCKmsXInbZDHI6yeB0AVB4sbmjjqrPHVtHRT4sdFva70/wB90q2+ZV04qJ3blpBi7SlcvCvTIijdICkqIzBYxC8MOFwYp6hhkka2sDqOiOLutJ/CXTlkqo57PlB9gtiFYnDHCwbU8+ySIBspwnEdfl+ETmLTMKiGBSkE86kAtqRT1ilrnGSxWB1B4V7Qt2vBSa/pCUL8NKWIIJP8UtCm7HF/VygCzVcGHV/KVNONQY4Q5ApTh+QEJZBAqYxHLcCLIpC+9kOAr7wr1yP5wZaZ2Kic4qlWIqSpRem2Tan5CIBpdVrK2cDNQfCWO7O+caKxWwoClIdwnCz+6o5K3LgDvCO0YcSmoDm/o8E3FbMMwbEV10yiw7LbXR4dS09mlKRKCjQq8vQO59WHrA1pmHQ9onaJqAAlMxc4AAJxJCSKZFlHX6zgSXJVMPACwqSSAB1UaJ7mEltqbpUY6tmTAtvsxY10/SHEuzSkKCpsxwKkI4ieQPl7uYnftikzZKZ1nCmSWWnIoJcgmpcEChdqEUNIkNU2lns+oqlzgmi5BE1LbF0r68OIn+EbQ9tCGlTQQzzEKHQggNy0jJez97KsdqxqGJCxhUPvJPPStDyJjYuPCmpVQKlhcoqNSkFSkpG5enrygXisprCCEtmTiflFklT0MUTZDHVgH/vtHiJjQvlCRSbWC1hCmU+AgpU2bHUc0kBQ5pEI76spUpbEKbVOVCzp5UePZtrGv16Qxs8gkDhdx7rGtTkNwD6QbbC7lCXNOEyQqWATNCVO2o4dOsSs010jeFVktplzyUuhRdvkQfhTlBFimcRTlnyiXAqCcI9fL+8DzJeukF2kDDQwtUog1iQ0oLV0izAglW8MrlCF4khTBNWINdC3LKBEETFBBOBHvKYkDbL48n6RaLImROw1APCTmRWopQ1DgjNJBi5p3EO5pVdSwOYRSdWWeEKplll+cN5IKqq1hFMCUnhL84bSrUSKBhrG5I4lrZGkAdSeVhVkgq/D0jyJ+CNxHQ34qP5gh7L0V0i0EJw0B/eS/wAHELregFTBu1B2FWhlNnhaWVQju3YwqKcSmB6Qlg2uc8tr3wVJdYDef7oq23NPkJKlScaAHJDlLfvEVA5xkbdaUJmJMslIeqdQOWhHeNFbLbMQgpc4WYsS1aZRjrxU5FWVUjt9fCKewuiMgcL9Oq1IZG7g0jHr0ThM1M9IBnYMJVUJKgcmcAjKtdHgIynOFO7u21XboHhfK8VYC0o1ZRGebOoDzV1FcuUNrJLmSvOlsQOFX3gTVtmZiKGp0Z8gtNrS4XT5CJYccan8xyHRLZ6V+EXXLbcE4KZ0+VafvJNCK+o5gQKpblo6UntAEZXAoP2pufw5pwh0kOmnmSqooYzi5RlrGNJAzemR+UbT2ktZVZpaGeagkI4fcZ3Wp2oaAZ0HNsYiepLJXk/o9ad9IY04pdWUyl1U2e22fm5/rDC1TTRL0Hz1J5xfcNjlqs5USypZIVkzE4kkakMoDPMdIBtLEuDSBDhwuINq1IChzMXWG3KkqceUhlJ+8HyfQ0BB0IB0gEKLUpEpqqh/gHygVIKCv6VI8RkqKkA5t69m9HbRyxl3hgCETCVSQrgUCDhfQEjJmLFnZiHEVTLuXOBUhHClgo7UJdWwoXMCXRNCMYmJxylMFy8ixfiSdFJLEdVbxJ4RsK0NrsM9lLTLWuQCQJrcLDU7NqcngCadmIigWyYkFCVLVLSaZ0owxjQjJ4kgE1Ov1WBDVJKlJlBVTEpE1WPhUpLEZEgZg5dh6PA8uaQS0FyBrQDMl46lFqdokypzhSiiYPIpquK1yChyoYgq1S0YhMlhU5gErC1ABtcIorP3g9Gga8iAnVwad8m6GC7kNnnYvGdKwk4q+YJriSNxkQN6bQR4sqLQ0q0TDqOtOsWyZGIu3rDVUlCQhclSVJLEIJBUKOyhUEc6PtnA6WT5qbAfrBIFbKkukgZa7mArztqihDJVjRwqVQBhVFc8QZn2QjaDZavuh+paI2axJmLCFzEyn95T4Qee3X5RLTRXVa65bZjSrGwUNOR1A2enKnONHY7QMIGEFoxEmZgWCaMWVV+R5GNhdM4B9DoW+EbUD98NFu6jwsfVRbX2DVpl4x2HoI9gfwz/AJsz0lf+uOh22X+W1Ve78ybrtaVJZSQS0JJaBizZodrtKSC4z/KE6Ql+J2iWM2xu7pHvf2QF1uGQUHe6zhzB7xmLSfT6MaC9pYAcExmrQqpUSwAq+w2HeOZiL9cK3Hyqrut0xCywSCSWGKm1T+PQ0hlar7XNwG0EpwggOAwL1FOxbrCCYQplJrqKA9iDGvkXoJ8kSlpQtWDCpSmxAIPCqtSzioaveMTVxhrtwytaB25teSX2dVSolx9D8IJVaElmA5DWK/siEApxjpX5x6jgySIqFMIUvCK0lz0DZd9adMzGcvqTTLKNJKWt2w06NCy9iitX5CvxjgpCR2O2HCzqzBDZKzoocnJBOTneDpFsSo1DHaFN2WhMuclRSFJB8qqAguGO2fwjX3pLkTSJqKOHLJIKnrXQnoO9CIJ2Ci5SmYa500j2XOSM/l8ItnzAQwqdOUAzENHCigOEciYgkAAcgREZgTJUFiqs+Q5HfZoXlTRTNmqNDlziaUg0tJd962eWQJqDxJYLAd0FLDxGzI4kHsdTA1ttKFl5aWQcmifspaJK1mVPlhQUCpGdCnzgAGtAFgZfszSsMr2uyT5rMeEFiAQU4txR3+GRpqJpNq0lSUjMNF5KAl/QbxROs6uURlcOjneOQFStEpRqrLlo/wCVPSFy5QOiqVOHPmz6s8GrrnFvhKAxJUxHzH4/nBcLgLWhn3MmSUfZ54moIAKVBiKeZxQAmpDBqiKLdZw5K2fDwEJVhUaFnoclOC2zsDDf2Hky1SpotCkoKZpwLxlJUAlKnqSFCqSAOcW+11rlqweFKBLsFhIGJiUsls0hv0EEG4tCTmlmJAYxbaUkcTMPn+cSSH68g0QtIUwBOKg0ZqOQHJJrrTpELkvmmWKqSS/NoeXHNlzEK41pIYBgk+pOWkZy3DTRqd+Zzg/2PmpExQUWDOOoP6xd0zqwbo+Sq6kd2xVjzWucffX9d49if2pH3vhHkXqb/Ld/vus7t3+Y+yaTZ6ClyntAUqzUClYQDkCqpG45dWyglU9JDNUaEN8awNOlJxOBT69IssiI3NDSPe/t5KpuBo2Cl99eGEsG5coyy5RL4Ukxr7TKA4xRQyqfiHrCGfeawzBIILgsXBBcNVg31pCAZGsIa37mytCBrCe8UhtlkWB5cIG4Zhl+cNvZqxy1SlOrDMctUMQwLClDV8zT4HSJqy5AlKGZTxy8ia4hiLB9aDLJhDAXctKBPEoJQp0lIOKtMTkpD1AD1cDR4yJ5XOsHH+FqxxNZlIMLBmLaEB3b5RyJpYeYw1tVqIowY8vxiqfhIofgRFUqSgCqYSWIA2pCu8EmpPy9YbWpOEB6vlmIXWlOIOBHLgVl7fJKVvocob3NZ5qpRWlylJYhxqCXHL9Y6RYvGSUFSXcsHqn+LYE5HKtYsuS1qsi1IUGJISUlNM24qghqEHkd4NxO3HKkNyrZatGrs20B4SIczrSM2fFUs1TzAApAM5Tk7vlENK5wVSSQWSB3+qx7NmIU6QmvICLJSgnOp6j4wumTMJJGcEhTC5bu8VaU4zLUmYkhacwFHC46Kwj+eGk6wLkAy5gIxOWrXc4jQ5bDIwouW8mmoKqBSvDUok0TNGFzUZFlfyxsb1vHxEJM/A7nyVDYinGwNXwuA4GehECSU0VSQKSEpd32rFa5qCHVntBFosiCSUAtpWvdqegikSW92IQlDLtLCiWfLPKApiypKtwx7eU/NPoYKtLvWkUWUftUpOSjhPRXCW5sac2ggoWrumeE2cS6nGA4OhljwgwDM6Uph/d1ls0wEKUzBkhZKVDXE9BvQPAlkuIySjAMZWnEohlBCi6iFEZJZgFEdWzixViMomfMIwpLIThLL0ZwQzE1pp1EGwDlC8pXbLKPEIlOQPuAgcIYkAlRajuTAFrpQBz9doNtCiXZKd8y28JbepnUmj1bP4wPVSqrxToBkNNd/wAYs9mZacSnLEMw6v8AkIQJtK0HMxqvZuV4oxmnEx0yavxi7AKIs19FU1LhsK0GMbj1EdFv2RG59Y6Nn4R3zuWPv9AnEichSXACkl2JGxqORGo0iNpSKEDLXrCL2ZmKTMSMeOTOo5phWkUChorTPiCnBLU0q0kUKCC2oPR6iKOl1G9wsd7qbr8K3qdN2eQcfRJrbm7CMveh4nbOsbCdKOQAfpCxHs6qevMJTmSduQFYsvc2B94AP3KCBrpMBKfZGTMmWjDLUlLAqJUQwABDkahyArkro2qmWiWlHhKcpSX4cn5O9Or5d4Y3fccuzIKU0J1z13cv67UhVe8gDICozChVs6Ri6p4e/cAtePutq0BeFll4mSolOhJDwqWGLBTHMExfPtIyVRtYEtFpTXCoGuY/UVEVLtHSAtaFE1YkE1Gv4RnZtsmoUeJXQvTtD20TDnCS8poIL56QbQu4QP2pQX4iSynoR8e3KNxcdzi3oC1zgk4QEKUk8JTw4MmUkNQuWcdIwhl8MbL2Cuta0zpgmBCZSVKIyxEIOZFaCoqziGPbQwoY68K83PNl8KmJS9QpJcJo+fozvSkJrVIINYdXqpSVKPEkgtV6MTr3MLivFUt3hYKNyXplhZaoMCz0McObQZbCBRJ0fsem8DLQCHGesEhpOvY24/tCjiSfDJKcVAMQQohic2JTRj5hDO2pMqYqXMABDAM1QkABgNAkAZaQD7NXpPCUpIJlpBwq2DiiXoqp8v51eKvMLqkgK/doTsSNTzhZJv0Tg0bUrlTXqCyeUez7Slt460z1O5JJ5mFdrnYjWJpLVVonpxZMBmOkHXGZc20IUAWQrEpwNAWatS4y5QmnS0nON1/s/s3hyFL95RJSUjiYUJzIYbsDpzggF1rQXbZ8aihSjLThqCak4mCRvw1yzBPKAPbK2EqEoeVAFG1qwB2A0hqu2rknFMISFSzVnJKFDR2HmSBl0jJ3jalHGy5mJVC5ADauNTkNGrBk0KQDJtAJWWIGegP1T9YVWibuYstc5SKuSRr+kCi0pmZ0MQ1tqSQqFy/EOEBycm3jWXPdBlgJKnNKAZk7RnbFZF48Schrl1aNpcpmILknEKjlGzoInE7gRjosnWygd1MfsS/uH4fnHQT/AIxO/wAw/wBKfyj2NPtJPT7rP7vqsvdVoEtJcEgmqQdhu3PbMco18u+0T0IRhUJpAOT7uXy08pL1yjE2O1yz50v+8CQR6Z93j21W1mloJcmhNGFCS4IrQBv7HyZbS9LuBwvocuVLQAqYRiH0zV1fPaKp98oyAfrT9YxK7aQmhq3yhdd9vUoqxEuedKaNpEOmeQobG0cLT3reiyKeVy+pb8QIVzLaKF/MH+MCT5tM4XqKRUMNDzhFkpm0K2bacRIPpAdsLg4c4jOnAPC9drD1IaGNaoKgLyxApWGUNd2hUtzVniycQtZUmjwwsFmOGpDxcjhPKrvkvCFMnhBIY7bRrfZOzeGFLXwpNQQmpwksxo9XFaCuRrCqx3cqYsaS0+Y77Acyx9DGpvq9CoYQEpSkMhCckJGQG5bXWFSmsBMjFZS+8LYV5ltun1rCO0qSnmYvm2pJoQawvUxcAvXMVf8AOEtCYSSqFEd4qAJIAqSWzbPrE5gaNf7FXWJaDa5hILtJTWpGa1B6gA0zq20HwoGU7tUsSZEqzqHFKSaBnJWcWJY906Yas2egzU2cyn2yhjalOskPXc1PMwrtU0vSp0haMleTrYk5/XIc4Xy5qSWcsdTEJqyVOcxA1ombZwQCi0ysF1GdPTLfCipUo+6lIJUfQd6DWPpNx2CWg8JdCACSoAGjsGelcJLjTOMj7A3Eqc85VEpLIdwHrXLiqGbkYf8AtDeiP9yhIKUmqjmVakHSGAULKEm8BD3peCp0wsr9m4A0YnIjUkmn9oztsmF+F25x7aV1BAYAuGJzGRO7QFbZuFatUkuByVxJ+BEBklTgBCWpRzgRMlzw58oKtcp0uC5OUG3JdqjknrrF7TwlxoKrPIGBNLisy6OKaOI18myumqSx1FPjFN2WUJSkEU1571hjdskyzMWuYVqVQCqQAS54XIGQA2D7xsn/AI2hjW880sZx3kkuVP8AhqNlf1x7BfiHlHQHZM+UJe93mvmd53XMknElik7Oz89jCuYFUJBG1Y+qWyx+IlZI4QHOXemsZqdcKVVSe2Xr1/CKztKx2C4bvJWodY4dMLPKUzVhYpWCaKw9vm6FIIIxDcUI7H9IQ2yQpACqgu2I/IHSM9+me3JC1GahjuCj5tqA2B2JA+GceWZOMH9ohPXHr0SRCNK35nrBNitiRRSXHX8hFd0RCsNcCj593Ub7RIB6zP8A1xSj2Ymq8syQvkJhH/WlIiu0WtIqlCCNiVuO+KIyrSks8tv4FlP/AFBUQ3c3hS9rXJjY/ZO0uSJCjrwFKx2KSQejxcu61YhLKFYiQAkgguSwocs849sdvKQMEwlyGQQynNKEEv8ACDbRf08krDqATgCwXo5JwnSoNTXhBh3xTi0tLUsadoN2r7RKErgSQQmhO594+tByAhNarTXntHgtSl+R1cgHPoIHl3RaiXTZ5yn2lqr3aEco6VNoGKpgZcwDrDSbcdtOEfZZoxFgMPz27wBfFx2qzjHPkLQncsQNKlJIFaViRSjKJuG6za5oQTgSOKYv7qBmdnLsBudgY3F5z7OECVKl0TQKKleufEd1HOFlyWD7PZkpJZc0CbMPr4aeiQ/dSoAvK2BFIEnoiXltW2Sux/Awp+1lwWNKEuPpotmKKqVJNBqS+QG8Wy7im5zVIkJ2WTibkhIJHRWGIUi0LalghwYWJLqAGZIA6ksI192WC70KHizpk0PUMJSTSgoVKz1BHaHFptVg4RZ7LJTOBdCwmqSKglSs8o4OFqS0rQHDZbKmWlgQnCnqRUnmMzzj57arYPEY/wBocTrxUVLRPbxE6aB60GmcZa8WUaU57ww94pdUirVagaJNNTA94VCFDMgp7pP4JKIWHEg8o0F0WFU4YEtiCgR0KTiA/oR6Q+KKyAEp8lC0NdV3zFrAFdWf1pG+um60Sw+FlHMuTTYPkP0jrquZEo4242Z9BvhGj/2aGUoT/GSEpQJIYrUrCcQ1/eSRozVqS0bDGCJtlufRZMkhkdQK6RZJgn4vFSJA91iVFhkQU0JOoNBHt4z1JCVIllZUWAAJAbcjXYdT1tvG1SpbYlMFFkgAqJ0oNRzgkyCg+br867NHYzTsquScW3CE+z2n/Lk/1qjoN+1SP/sI/qR/5R0K3f1IqHyKqU6WAJJAzIziiZLdJagDqYD5DeLZiEzZYS5SDUK/BQ16RGRKKQAVYiNQ4psfvdYc05oD6FIIxZPtwltnmiY/C4GYPPnAN5ez6FpKaqBySdO+p50jSFL0yzpl/Z4CsCppKgqUpGHU5dAaOeYpHO2uoSZKNjnDLOF8cve7VSFEZpeihUHkSKPAkglxH3FF3ynJCEgqoS2mtMh2jK2v2VTMnqSLOJUtOahR/wB4EcJJ2GWp1inLp/ytOHVCsrEz5NAQhuf94qlyaspTcgCT6RqLb7LTAWEx3dgcyBsIWWm6DJeYtJwJFU1JUdAfup1J2G5EJk0UjBdf5VpmqjeaCqlAS04i5JFMnANH1bFpnRzqIlYLdhclKC+QUQT6Giv6YQ2i1rWSVKJJL8uwyERlRX7DGU4TAHC1M72nWkYXIGycQHRqD4QvN8KUXEyYOgH/AJQGsHDVXaISlE/rAfDtCZ27lorBeUxWU04g5ZTjTXQip1htZfaOYUlCQmoZRUQzHkc4yCVNmX6QUi1pSGSkvufnAdgp7Ypn9rUFqRMLkDN/xcvAk6ypmzE4lFIzU1SRyeg6n0MJ51qLu5xb7RV4qvvQQiKDeOq2Kr0l2dGCzSQkmhWVYll86nIchTlGetlsQDxArVs5Ce6s1dEsOceWa9FI8oHUh4la5C5o8RSgS1BtAhm05Rl9jCrlXoseUIQD92WgH+psfqYdyEO82cshTUT72Qbdg29YTy5KJaQol17EABHMVOI9gz5ZRV9sJycnUmHCO0tz65V94qdWLJ60+UeonY0l2cRZdtzTJ5CjRJ97SNZ7NeymFSzaEIKR5CC7l82HutuxcCLjdITV8Ko/Uhqzlw3Eq0TcDswcliQAPk+jx9Duy7JdnSyEpxsxW1SNidsvQbQzlAJSxChlhagAHLLUwPZUzcajMVLMr3EpTXUAk5g1rUueUWmMEYqrVB85lJo0oIM3xgnAjwQKrJcq6MeE6MQRQlzFlonoQQFKw4vLRRJq1AkHXWPETEmYZYWnGKlGobfR+TvFhAC/EwDxAGx6jpz0faGUf+ptVi5prcK/yrTKZYJQkqTRJwgqGdAWcZn1MVWmT4iSleIAmrFiW0NDR9OkRmBKwApRAd14c17Jd+ERK22hagBLCRoKhkAbjNXy3fWKNkbUVYB3KH2Oz/5Kf6l/+UdA32Zf/wBpX9A/OOiOz/pRb2/P+B+qYqWVJJYqIDhL1PQxRYbQFpVQjRSciHo4MQs0sJcJKmOQNcPQ5wSSrU9ah+4zgy09fsqocPqULZbJ4bssqByBGXPPOCgsYmJD6hw46jMRVNWpKxwEoOSkuqvMafWcezLNLxhZQAsF3FATm5GRP0YEYw1H6uwqxImiZi8VJlH3cLEbADf95+oOUXGYzYmqWDkBzsHzMQts8S0eIoFnbhDtzOgH5xRaEyrSlJKcbZF1Bg9QoBvT5ZxHhGMpje9zgIS8rmlrm4ypRJLmWcqc80JHc7VgH2iUZaQpioqJJLUDZu2T6DYGH60cCihOJQFEggO1ANGAGmwpA1imTFAlSFSyC1demR+DVgmDbe00SpMhI8wFjp3semclMzB4SljEwoz1BPu1FchnCj/4apQxS5yFj91i3ViW7iPqE+WJiVS11xpYseJjqNRk2xrAt2XRKkBYRiOMhyoglg7AMBuT35CJcA4jc0HzPH9kxmoIbysBL9mpoDYUq5uR+ECLuG0PRAEfQbTYbUbUlcuaEWd0ggKNUpYrCkEMVKOIPzG0XX2ZqJRVJleIsqAAYqwipKsIqcgn+aF9lDklp+6f8VJgAjK+Zf4BaAfL8jEv/j9oIJKSlmzIr0aPqVksRUiX4icKykFaRRiRUB3I6Pm8LLhXPnFYnWfwglIY4Fp4iRw8ZL0c02ghFBjlD8RKb9FhZPsyXHiTAhLOVVJBdmw5nfmzQst91qQSygoCuqT3Spi/IPH0i/7DaBg8CUJjg4nSDUHKpAAIb4wxtnskhaZgloAJSrAqrJVmDTnQsMnhcsMWdpTo9Qdo3DlfGkyi7MX2Yk+kO7pssyaPDloxLbEzjIMHPqKR9H9mrhMiThmlCpmMkKSHYEDhKiATUKOXvRKRclmkTzaA6VkqU5VwpK3CmFBXEc3aF/Dg1a46wNJpfPrd7MT5XhlaDMxvROIsQapoCxIYg9do2cj2NkBDFB4xqRiS4B6AjuM8xGks87EAQQUn3klx6wJYV2hcxXiyUy5TEA+IFKJBajZg1zA66Q8BrMDqqzpnSBLrLZrNY5RGLCnM4ySVFgCQkZlgKJGkMJctK0uPKtIKVoZ2UHCkkhn6iJ2uxS1lOOWhZSaY0vnn/bKgiS56zMEtEhRAIClqIloAp5KHGw29IMu246JIt+Ryq7NZUSJJCpqiHdcxaiKmmQ1J0qTuY6QAoCZLUopNXLg05H584NW6QW4geWfKKFFZTwqSlWpUlwOgyfrENsccKC/d4uVXYrMiW4QMIV5imhLd/hHWWQsLKllJ0ShNRXVRUlyYvnzUoSkKKlKIowBWvsAAOppElIAAJpyNWO1Mz0jrBQOe8IATMaykIUUihWXSH2QlnV1pFsmSHIqQMyMgdn1PIZatqT4Ldfz0giz2MkOeFA+qCDL6HKQQCchB4E7R0MsEn974R7A9r9VGz6II6dYWXl/xY6fhHR0QfEETP4bk4PlgYx0dBNUv8IRlhgCz+RPf5x0dCx/EVlv8FeDzRdMzjo6HHlVhwVi/ar/i/wCj/tpjZz/OrrHsdC2cp0vhC8REpUdHQZQN5UhnE1x0dAHlNb4SoiDrF5FdDHkdATeFHGg15Rh/9ovns3Rf+iOjoMIW+NaH2Q/4GV1X/wB1cOlZ946OiB+q6TxKy35jp+EQ92OjohvhCAeIqq0/7+T/AAL/AO2qKZmUex0TFyon4aiJXkiQ/wB8n+BXyTHR0C9cfE3/AHoVHWD708qekdHRDvE1AOqUx0dHRYSl/9k=', stock=40),
            Product(name='Thịt gà ta 1kg', description='Thịt gà ta thả vườn, tự nhiên không hormone', price=120000, category='Thực phẩm tươi sống', image_url='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxMTEhUSExIWFhUVFRcYFhcXFxYVFxgXFRUXFxcXGBcYHSggGBolHRUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGxAQGy0lICYtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAMIBAwMBIgACEQEDEQH/xAAbAAACAwEBAQAAAAAAAAAAAAAEBQIDBgABB//EADkQAAEDAgQDBgUEAQQCAwAAAAEAAhEDIQQSMUEFUWETInGBkaEGscHR8DJC4fFSFCNikkOCBxYz/8QAGQEAAwEBAQAAAAAAAAAAAAAAAQIDBAAF/8QALREAAgIBAwMDAwMFAQAAAAAAAAECEQMSITEEQVETMnEiYfCBkaEUJDM04SP/2gAMAwEAAhEDEQA/APp9d+VhKWcPpgiSu43jL5BtqgKWLyhORlNWMcXVa0JKHwZUMRiS4qrOuFcrNFg3yLKdTEg2m6TcPxmU30VfEa3fzAoS3RSM6GnYXlSBlKqXEXb3RdDiTeSyPCzXHqI9wmq2RohvJXtxzCpDFMSehIp68CoxGiqfgsw0RYxTdgvTiCdBCePTvuycupj2BMFwwUzmcVVjaheeg0RtR1roTKtMYqKpGPLkcmUMpJnQoCEOyndMabYCIkRRisP3gpYmh3UcKUv0R7OG5rnTlujZyi3wZZtMzomWG4ZVcNIHM/ZaDDYVjBoJFyd/dEh9x1Q1srHBXIowvBgILjPMbI8YZoEBoRFUE6LmsgapHbKxjFcFDHjQsHop4ilLZbbwXpezdw+qqbiabf3hLW27H+BTXdWpnNMhWU+JEn7IysaL+652qyvE2vwzx+6m+crh8iozi47o0Y6m67mroVc+0Qi2BLuAPDqeYbm6aNatOP22Yc3vL2KusrGBVVynJvgAcLri1S3UnBcToGIXqk4rxABlXOm5Vb1YAuLURAV4VcopzFS9i44iHr10kKeHwhcU8/0IDb8kR0mzOAqQch+IV++cugR/DMBVqgHLladHOsErDCVukL6mMylMcDXzCU1f8JhwltQFw6W9VZ/9bexoyuBO409CutUamtuAei4K7tEtq1S0lpBBGoK9Y8lcZZTSGjmSFWxijSqmERhqU3NgusEU5PYnh6BJsEzpYO11R/rGsiIMDyQ2J42bhpHSbzzlI5o1ww0N2UQImB7KbsQ0XJ05bfdZo8TeZl2aY6Hy5LnVp1N/dLr8FNA/ONbtHgTBPkvDxBm5A6AkrM1Hm9wZ56qHajc3Q1sOhGsHEmkquv3mktOl7X81maVRX08WQbGDzXKfkGnweVXmdUPUqnyVdeoSdNeSHebawpydjpBHaqbHB4yONtp0BQPbc1MVVOyqRs+FYXs6YbvqUcxLuC4kPpi9xYpiFtjVbHn5L1Oy4IfEFWFyFruTCNlLDdSLlU0qTigIVuK5RJXLgWZstVgavAFYSiIUEKD6auhTYFxxdwylCI41VhkDde4WyB4rjGhwm99EW6RSMXL6UL+H8JNR02yg3JMf2tTToBoBLpjbQeCz7ce2bR4Dx5Kx+NJvuFGUkzfhwaFQ9q4/yHQgj0CnhcYZgn7fwkdDGdAWnWfkiKdXI7Kf0O0O7TyKCdsq12HHEMBTrAuy94Cx3EbLMMYnox+WQdRvzH1QtFjXPc6xkyB4p9SMebA5NNFeHw51jwCNxLcoiR+c5soPrZY5nfT6JfVrExffe6RyKwxqKpAmJqEnl4HfqqZ8dE7w2KpsECm2RuQHE/ZHUeJjkBa0ABJsUtmYZU6SoveYgCd+q1ddtKo3LAa7YhoBn6rKYqlkcWnYwUODirtSphu0KkNsTfVWtHy/CutHUG4BmYjaNSRIFlU923XzRFAta0mSDy28fJCVnTr6oy4BHkg5/kqaj7c1J8nkVS/wUmyqRCV1N/NRc5QLpsNUpVGo+Eq/ec3aFqgs58M4bK0vOun3WgY5a8aqJ52aVzZaQhMQEWSha6qQYO0LnqxrVCoEBSglcvFy4USAK+nhyRIVQCe8No9xEEVYhcxcxH42hlJQQC4DVBdHRZT4ixtNlVrHvDXEWmwMkACfP2WnNcU2F7tAJWCr0HY6qMQ9zW0qTpDQZe8tNgB+0TFz5KWWaWx6HRYXJ63wgugwkcgNeh6+dvRMcNUMQbj80OiDbTvAMgmQfzUjTqjaQEawdQfsdxbRQ1bmtskyvl1/S61/n462VlXGS0sOrbT7oSoZa4Ea6jrzCTuxhIaZvoTzyotjxSa3HzuIlzQOVgfJF4DE5Wi503uSs3Qxed1yIg5Qd0c6qY8AluhH4GWJxRkDfaLk3si6tMwBPjfcfQfNAcIwx/8A1O5hgOx3d84Tdw7ugP2Twj3ZObrYGqUyNj5L3DsMi6kWyLEg8vzRW4Wd/MpnSJphl4ufIJNxJ8u1PmnR0sLrNcQrEVSHGw5dTpCnIeJY0DT+FMzMQPzwUKUHxKIFNubSPujFJoWUqJVHHTz9dT7Iep/Cuq1J3kDyhDOPO6ZrbcET0HoqK1h0VjG8ioVnZhfUe4UC68gLnq7DMgzuo02bnZX4Nm5XXRSrNd8OEFhvum4WTpYzs2jqnvCcTnC045bGHNDdsZ5lTUVqgQrGZlSpqlEOQ1VcKytcvVy4UU0mSYT/AAbYCX4KhumDSiNBUQxtIFJ6tKCnVRyWYlt5XHTQBxPBCrRcwvyb5thFzPRYvhWEDGk5gQ5zrDcWAcD/AOq13HajexdTLi3tBlMRMHWJ3I3WXDGtgNnIAA3/ACbFr81kztatuT0uj1LE0+AimSHkD++o+ytxUgWFxfxB8PyygfQgiY5bOClicUQAesHb+1Oytbg2Jxwawv5D8HQrP4atmDWDYEnxOyD49xLM91Jk2N9om8Tui+E4XJF5I1RQW6VGhoYcNaDquoDtHhoFtSRsBr9ldhqRqwJAaIk/OOqJhtMHIInmZPST6pqJph+Ednef8WCANp2A8Ar61aULw2lFNs2Jlx6ybe0K5xv1VIqkTnySpkmZ/PJX0wZ+iEwz+9BEnXkExww5GTzQasSydV7ogGPzqsfiCM/ddmEyP7Wn4jUAaTUMACT9ljcNUEnLpJDb3jr5JJFFwN8LUI1ElGNqbaR80BQKJy/m65JoV7lpPXqqTryKkJ0jzXgE9R7oylsclucTAlRxBtYyNvBTLb29CqMYYtppCki/hFYvAhGURZC4fTxRVFAoX9nJEjb5rS8Bwpa02InmpcJFNzG5YMa+KaMC2Y8ek87Lm1Wke5VW4K8BQe1UIg1QoWoUTWCEcgJI8XL1ciKWBSlQC9lMVPXlBYwhjC92kWHNE1a7WgudoBJ+yx3FuKdq/oRYfRRy5VHZclsWHW7fAFxrEZ3HNc7xIgWMjnCHYyx2OXycOYXtS8DRwMe1vEH6qdBw005TsdC3oFjk/Jv7UeyRvMC3Vu4SrjuPaxh0J2BNzFxEJnUjbxH1CyXEHdrVygjKz6fkIpHLcF4XgiTncCcxm+55e6dNMOyC0lRp91sX+Q8VbwhpfUnlpvfVGzqNJwui4U4P7j5wFz6faOLRoNfVGBwi1rRzgL3E1GtDWt3NzOttSnulRNbuy+qQBGwAAPLwUcsCPdVVHTHvyHJeVqoa0Tt7yqLdEpI9wknNJtMTzThshotY2Hlul2DhxBA0tp+Si8XXiJOVdJgSsTfE2LY2k4PMlwytH/LUehAKzWAf/KI+L6zXmnlBluaZ6xHyS7h5Kk+Sq4NDSKPok87/AC8Utwt/smdD+03AhcWDw+qiKMHl1GmiIY0abLg3kY8UuTg6J1OjvY9TsicThadcNB7rm2BG/iqGPIIsCri4bCDvHt4JFsO2A1ODVGaDMBuD9F5kc0GWuHknFCv1v13RLcYJvoelxHzTaFJbbHeozN4Li5ouAEkDVbvh+MZVaHMKXitTn9p5C0dDK5nEWt/S0A8hb+1qxRhjhpS/UxvHJyux0ouKWjio8OiHq8WGy5zoZYfLGFZ4GpVYqU9x7pJieJE7IU1nzM2Wd53dIr6MUjTf7fVclDKwgXXqvq+5L014GELwmFZCV8dxfZ03XuWmPGLKxIUcb4mXEtYYynTZyzlSp3wIy3PlKrp4kGZEjY7g3NvNE1sNnEtOYjY6rzptuds9SCUVQNjnd8E2nuu8dj4Lx7jqPHexbr6hXmgKjIJ7wsCemxQzgXd2O9ofSPHkhdsK8FeNruiGzJIy+YQTcKKYgkA7nVODQFMXBcY1gwI2QGMqiJ2PRFsKF+Jq7aplwBhaM2huR7D5JJGd4bO/tutJhzALfzoUIgbDsQ85CJ/Aq8FWLw12tt9J6ofiFaKZVfw2S+mO7JBdv/yJ9bpktwXsO2VSTrJtA2FtT1V4p5iZ+n1Q9GnytrMougyY2/N1WLISDKDC1vdbbcyqXPYDBMnl0V+Iqw29hz+gCGyGHENERN7E80s2+x0VsZzjtAOlw5kpDRcQVqsTceKy1cZXwi33BDwaPhjbSnDG2WY4fxAtInRaChxBpFipyklyNoYS2orXVRGw5zslz8Q3USuFcHXzCOpM5xoLzjSDzXgqARHnKEqYk877coUW1TlAnfTkuSViuw19c9CvW1TMdPRCCqZ6qmpiL3VNjhiMXtBhd25KWdv1vyQ9fiLWySY+SpaQjHlStuSqm4kZS4G2gnfwSTA1nV5e4xRG+mfoOi8r4o1Xd39MgMaN+ULLmzS4iI5UOO1eRIB1tAMKVOs+YIJ6Qn/BOHmlT75lzoJGzegR7WidAqQ6d0m+RX1PahVQwlQtBDIlep+3RctGlC+ozzKs58SsBZUdP6RHyn5rQ51k+K1waeIESc8z0zfwquGpc1QNSTRiG1C0gzbN4R5ppgcXABt4kcuo1QlWgQ0EiztFVRJbAg/qBBWLJG1ZvizQ5WPMkhruYOvjzXj8JeSA7aRyQdDEDQ7GNBoUxoV9ufIeoWZ2hmLsY4gZWgxGukeKzmLJ3WxxVJrhrH57JJjcFTF3Eu6aX8kurceIo4S3vF3kPP8APdPaDbygmNEd0ADorW1VdMWR5xN1iF78JOsWwbPnpoFTiqi94DicjnNmxII8dD9E0eQP2myaz2vChmIIIFuXJUnEiAQLqzDwTMwdhNlREgh75cJEu2be3MlFjCjV38DwCpZS7NxLyCXAaRYeKKZVbYz6802nyLq8FXYCItHUa9Uuxvw/RrODnNgjUsIaD0Ij31TxhDnXgk8/5VFSlqUrxoZTMlX+F6gc7si1zP2hziH6XBtBPmkwq5DlMtcDBHgvoZLh0HqUPj8JTqscx4kkWdAJadiD/KnLHZWM6MfRxRiCiKde4QnG+HPw2XM8Oa6cpiNDeR580vGKuhGLR0mmPjVne3uubW8Ak9PGjmufjRrPROtibHL62u6Dq4wC9+on3St+LJsBppyVZpOMl1j803KECa3EibDvco/NF7w7h7657SsS2k3XbMRsERwrAj9R7rBqeZ5BVcQ4iax7Kn3abbEjcch91GWStokpyoJx2P7T/bZAostbeP2jomnAsOQ9jwBnLgGNOgvAlLOF4MGHERTb+kcyN/Bar4WYH1S83y/p6EbqMWnJK6+5Pnc1NTrruosXtQr2iLr1TP3CGhcrWhcuKAFaoAElx9MGfybbq7EV0m4lXcC3vHKZEW11+/orQjb0k8k9KshjOHBzIFouPskDcK4gkCY1G46rR0K5c3qgauBc0yHa+qhkx06NGHNqQiFJwmDY7FWsruGo/vn4q6ob3UIOyzygalM52JPXx3QGIcT90XUeeSEq1UmkpGRGlUgQptqT56lCvqBDvrAaFDSFsLrEzbzKCNQzI2UTjNifoq3PkdPz1XUxlJGh4VxsOhpMHYHn0KfU8VMbL5vUM2v5WOvJSZxOo0yHkxsZ/CjYHFdj6a+jm0e4H19kFiqtencZagG0EOA8FjGfFtQagE/9Sm3DfjCm4HtAGEcyLjnJ1jkLpnICjQez4gMzlg82m/umWA47OjoM6Gx8l8+x3FQ6o9zYDS45YtA2hdQ4oZtqOiVarObifVKfFrgb9fsNVY7HZpEwvnY4wbOqNafHX+0Xw/4lYHQQ5o63HrqFZavBJyh2Zs69FtVj6biSHg3Ox2PiDB1Xz3iOCfQqGk9vUOBs5ugcPe2y22F4vSfaWnzXvGOHNr0+RYczSfcTyP0CV87BvuzEigIsFFmGK0tHhoa24SzFwDZU0VyIp+CujTAVwwsnO8wwbDV32CkxgaJfb83QFUuqmG91nPms2TL2iSnPsTx2OdVPZsswWMWtyH3RPDcCCBaGA/8AY8h06qvh+GkQP0DUgQXHkCj8ZjMrQxjZcRDQNhz8FnVykoQ5JN0tTPcdj25hTHnHyWs+FK0U3vyQ1th1Mf16rGcAweat/uAySZA59Z2X0vA4fLQDHQWz3Q3a5IJXrf0OLHWpW/4MsM2TI206ReSrsOhnPRGHK4ouQ8LlAFcgUMe4yh8Zhi5sDXUeIRNRSziEybTtEavkp4bw8NOYnUe6ji8K1x10tPJXNxzQ4CYlXVsoMRA8LKWSUvdKX7lccYxSSRh/iDhFZ57j3NDf8TEpNTZj6TYlrxOr239bL6VWoXEIDFUJHRS/90t4pr8+B7V7Oj5nXxeLcYc7L0aMqBrVKh1e4+ZW54lgRGbl0SbE8PDhITpN8xotCfazOnEPiJMIR0zKb1MGQqjhF1FUxc4HmV4ys5mhPhqExGFXP4fOqDQLoEZjidRdRNTMYAJRBwgCN4RgyXElpPKNEr2QYttg2H4S513TH5um+G4Uy0NnnbTzKZNIAALS3W0FXcOqAkR5DxUW2yyoGbwZh2HovRwEGwGXqLJ06mCba79JRlKkQBM6a2H1Sps5tGbHBMjoc0O84PvKm3DUhZ4yH/kLR4hOXvN7AidryP7RNfDtjvgaTz/CrQzziQyYIT5BOG4OjUbLXB3VuyYUqDWCySUqIa4lvcjUt+qlh+JS/sy4mxgkRMfNWjn18kngUOA/GV5slnYgf7j7NGg5/wAI/DUDVMx3QfU8lPH0WAh1Qzl0btPgs3UZ99K/PsdwJ3UTU79Q5aewP7uvgoZe07tP9E3Ohd0HTqr8Q3tbvMM32B6DmvW1JGVoLWC2hDneJ2aoJN7fiJNblOM4gKQyAidMo0toT9lLg+Fe4mo90ZtdJP2VWIwrCQ0MA5uNvb6oyjjWU9XZiLQNAvT6f+n6eFt7v9X/ABwZMqyZJ0lsaTgHCg5+2XVxJv4E8yn2IrNDi6QABAJsI3/OixGH4hiandpNcAeVvMkovD/DlV96tWJ1glx9TZCfWSyf44t/Ow8MSgqbHeI49Qb+/Mf+In30QI+KnuOWjTk+BefQInB/DlBmrS883mfYWWgwlFrRDQAOQAA9lHRmlzKvgonHsizhlV5pNNRpDyO9oNzt4QuRAXK8Y0qsNmUroOs+bI2tCFDUxICqUDqjMBiphjwSTZp5qYpq2hREzyQlFSVNBg6YY9uUfRDOcCDaRup12EmxInzhX9ixggEuJ/VJ359CoSk8cfqdR/cuo3wKK9Kne0TsSlWJ4WAQ4SPlC0NYsmHNMfI+S9o4anBgkgnrZPiyQkqxz/SkBwd7ox2J4YHXFigDgYMELdVMK0ySAINjMg9TpdKq9IXlvmLhdKUYtJsqpMzRwI1S/ErR4pnd7pkLOYyb81ze2xSO/Jdg6DdYueae4amYaYMTByxEecrLsxBy/kk8lpuHCBmgaGfzzWWdmmNDVzA5pLdQbzrCofQaB+nxtCia4AE6SiGAVXZG3IseUFLFN7BYrxePFO8AHTbfSB1ka6XQNLidWpUipIvpyBsLDffzWqqfAFOtlc6tUaW3BYGi8yP1AzH1RDP/AI6p5y//AFNVxOzhTtGkQ0Qq+m6IqSvcz2LAY0jNO8Dx1XjuJHs5Pe9ot/C1TPgSlfPVqunq0e+WUwocBwlIR2TXR/kS/wBnGEuhgc0fPeGGvWns6TnayQLC0fqNvdMOFfCD2v7bFVRbSmwzppmf9vVaXjfxBQoth9RrOTd/BrRdZo8TrVTLaTm0/wDKpLSfBu3mpyk1wJKTY9qYum2zRppsAs7xHFMBNsztz+0fnVD4jtHfuJHJth7aoX/TOJAPdB0n7bqMdTexJ78HPrEmS75QPBVlz3WaCn+B+HmaueXHwgeyb0/h5zmxORnMAj0m5WiEMPOSS+F/wSSml9KMZhOF1HuyiSTrGgHUlaTh/wAPsYRJzum83aOg5rRYelToNyskzrOp8eXgotXp+ngUaUU7Mj13cmWU2gWV9IKlqJZokSSVIa23bJNCLpoZgRNNEeJcCuUVyA5laii0KwqLguJltNoXZoUGPjZeVXrgEK1eEBTr5XS1x8DceilVIVJp8gu0qSphjJxewfheMseYdE8v4TGtgZAc0aibLBV2kOI3CKwXGqtKwdI5FZZdDDfdqyq6jyadzKVOS9pBOp5+JGqDxDWmTTgepPsuwvxKxwyvEeNwpO7KppAB5WHstsMGNxUW+O5KeWfK/gyvFKbmGQ8lIa+Mcf1Nnrv6rf1eEzZsGeaWY/4bABcWwee3ok6rJixPTy/A2Cc5bvZeTGsqmY0AE+abYHjTQ4UtXbzECbT0QOP4TX1Y2W8ufkkeFY9lfM5pa7fy29lB4ZJXJUbY54y2TPoOJ4i1jXF4vG+mliAm/wAC1WmiKm75cfM/ZZLG4ylVpntBMB8AGDp9Lqr4L+IW02ik8hv+OwP2KXHHuNOVbH19uPEwva3GGsG8+KyeB4m19QNDgSQbTyTzsmuacwnleFRbsWNJ7gWP+Kz/AONjqjibN+tpsllbD4uverW7Fh/ZTs7zMz7+SizDltZ1S4MQ0c+ZTWhhHkTDzPT6pJ6pPTAHUOMJfSAYXhWGw/ebTDqn+bzmd4ydPKFCvVc54kF/Qd1o+6cNwJv3QI1mJ9yi8FgGxN7b6D1WZNKfaX2I7v7CnB4TNfJlJ2uQAPYI8cHIMloA/wAjr1ReKxVFn7hMRDRmPrshTxl5blaIGxN3Rtf6wtWSDywpfSD1FD3MOoMZSE2nmfoENiOIF2nqdf4QEkmSST1VjWoYekjBK9yU+ob4JsCvaq2qwLUQLWolmiGYiW6IDosphFsCGpItoXFEerlOFyAxk3Kty9XIkyIUaq5cgcUQiY7q5cmhyAWcSYMpMD0WdcuXJ5k5ECvaTyCIJHgYXLkgFyabAPNrn1TLHuPZ67herllr+5x/KNWX/DL4KOGtEmyB+IcKxzDLGnxaCuXL3J+48zH7DJYPDs/wb6BM8Tg6eQHs2TOuUT8ly5Zsy+k1YG9TPMJRa2rSc1oBkXAAOnMLbtK5csMuxvXJXhR3id519E6w+gXLlj6H/Yn+dwZOAHEC7kh4nVdYZjHiVy5X6dJN/JOftKKCPprly1mIvarGLly4Ja1TauXIDIuYiV4uQKIvpIti5cuKIuC8XLkBj//Z', stock=35),
            Product(name='Trứng gà ta 10 quả', description='Trứng gà ta tự nhiên, lòng đỏ đậm đà', price=45000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1518492104633-130d0cc84637?w=400', stock=80),
            Product(name='Sườn heo 1kg', description='Sườn heo tươi ngon, thích hợp nướng BBQ', price=160000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1558030006-450675393462?w=400', stock=45),
            Product(name='Cá điêu hồng 1kg', description='Cá điêu hồng tươi ngon từ vùng biển Khánh Hòa', price=220000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400', stock=30),
            Product(name='Tôm càng xanh 500g', description='Tôm càng xanh tươi sống từ đồng bằng sông Cửu Long', price=180000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1565680018434-b513d5924217?w=400', stock=25),
            Product(name='Thịt dê 500g', description='Thịt dê tươi ngon, bổ dưỡng cho sức khỏe', price=250000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400', stock=15),
            Product(name='Cua biển 500g', description='Cua biển tươi sống, thịt ngọt và chắc', price=320000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=400', stock=20),
            Product(name='Mực ống 500g', description='Mực ống tươi ngon, thích hợp nướng và xào', price=150000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1615870216519-2f9fa2dc15da?w=400', stock=35),
            Product(name='Thịt hến 300g', description='Thịt hến tươi ngon từ sông Hương', price=80000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400', stock=50),
            Product(name='Gà công nghiệp 1.2kg', description='Gà công nghiệp sạch, đạt chuẩn VietGAP', price=85000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?w=400', stock=60),
            
            # Đồ uống & Nước giải khát (12 sản phẩm)
            Product(name='Coca Cola lon 330ml (24 lon)', description='Nước ngọt có ga vị cola truyền thống', price=360000, category='Đồ uống & Nước giải khát', image_url='https://bizweb.dktcdn.net/100/423/822/products/24-lon-nuoc-ngot-coca-cola-320ml-202102082302425380-jpeg.jpg?v=1620533626720', stock=50),
            Product(name='Sữa tươi TH True Milk 1L', description='Sữa tươi nguyên chất 100%, giàu canxi và protein', price=32000, category='Đồ uống & Nước giải khát', image_url='https://image-handler-prod.s3-ap-southeast-1.amazonaws.com/supplier/654/PRODUCT_IMAGE/bf25747c-cfb1-4450-b66e-868d3959f5d4.297', stock=80),
            Product(name='Trà xanh Thái Nguyên 500g', description='Trà xanh cao cấp từ Thái Nguyên, thơm ngon', price=180000, category='Đồ uống & Nước giải khát', image_url='https://i.ebayimg.com/images/g/nqkAAOSwInBnqcbO/s-l1200.jpg', stock=45),
            Product(name='Cà phê Arabica Buôn Ma Thuột 500g', description='Cà phê rang xay nguyên chất từ Buôn Ma Thuột', price=220000, category='Đồ uống & Nước giải khát', image_url='https://m.media-amazon.com/images/I/41v1AmmYF0S._AC_UF894,1000_QL80_.jpg', stock=55),
            Product(name='Nước cam ép tươi 1L', description='Nước cam ép tươi 100%, không chất bảo quản', price=45000, category='Đồ uống & Nước giải khát', image_url='https://product.hstatic.net/1000180066/product/upload_d728ff2b444140069f9e1cf04c086dd7.jpg', stock=65),
            Product(name='Pepsi lon 330ml (24 lon)', description='Nước ngọt có ga Pepsi thùng 24 lon', price=340000, category='Đồ uống & Nước giải khát', image_url='https://www.vietsanmart.vn/web/image/product.template/1367/image', stock=45),
            Product(name='Sting năng lượng (24 lon)', description='Nước tăng lực Sting thùng 24 lon', price=480000, category='Đồ uống & Nước giải khát', image_url='https://ctproduce.us/product-images/ZOHO+THUMB.jpg/5236170000042078091/600x600', stock=40),
            Product(name='Nước suối Lavie 500ml (24 chai)', description='Nước suối tinh khiết Lavie thùng 24 chai', price=120000, category='Đồ uống & Nước giải khát', image_url='https://cdn.hstatic.net/products/200000459373/n.kho_ng_t.nhi_n_lavie_500ml_1f956a91048245de96077c0b016c16f6.jpg', stock=100),
            Product(name='Trà sữa hòa tan Lipton 20 gói', description='Trà sữa hòa tan tiện lợi, vị thơm ngon', price=85000, category='Đồ uống & Nước giải khát', image_url='http://bizweb.dktcdn.net/thumb/grande/100/514/431/products/tra-dao-lipton-hoa-tan-hop-192g-16-goi.jpg?v=1716434392707', stock=70),
            Product(name='Nước dừa xiêm 500ml (12 chai)', description='Nước dừa xiêm tự nhiên, mát lành', price=180000, category='Đồ uống & Nước giải khát', image_url='https://nongsandungha.com/wp-content/uploads/2025/01/nuoc-dua-xiem-xanh-cocoxim-nong-san-dung-ha-tien-loi.jpg', stock=35),
            Product(name='Sữa chua uống TH True Yogurt', description='Sữa chua uống có lợi khuẩn, nhiều vị', price=25000, category='Đồ uống & Nước giải khát', image_url='https://product.hstatic.net/200000452921/product/loc-4-hop-sua-chua-uong-th-true-yogurt-cam-180ml-201905060959279602_fcc6b8fa2bce4a4aaf238057e15eaa92_master.jpg', stock=90),
            Product(name='Nước ngọt 7Up lon 330ml (24 lon)', description='Nước ngọt có ga 7Up thùng 24 lon', price=350000, category='Đồ uống & Nước giải khát', image_url='https://product.hstatic.net/1000075554/product/-huong-chanh-tu-nhien-330ml-lon-fti9v_cdbf06fd2146465387772d661d66fc20_527e50a0174f43a2b5f38ecde6dab774_master.jpg', stock=40),
            
            # Trái cây tươi (10 sản phẩm)
          Product(name='Táo Fuji Nhật Bản 1kg', description='Táo Fuji nhập khẩu từ Nhật Bản, ngọt giòn', price=120000, category='Trái cây tươi', image_url='https://minhphuongfruit.com/upload/sanpham/z2402069921672_9b7bcd8a2967ddf5efdd15f5e5004de5-1959.jpg', stock=60),
            Product(name='Chuối già Nam Mỹ 1kg', description='Chuối chín vàng, ngọt và bổ dưỡng', price=35000, category='Trái cây tươi', image_url='https://cdnv2.tgdd.vn/bhx-static/bhx/Products/Images/8788/313132/bhx/chuoi-gia-giong-nam-my-1kg_202505201047413543.jpg', stock=90),
            Product(name='Cam sành Cao Phong 1kg', description='Cam sành tươi ngon từ Cao Phong, Hòa Bình', price=45000, category='Trái cây tươi', image_url='https://nongsandungha.com/wp-content/uploads/2024/07/phan-biet-cam-cao-phong.jpg', stock=70),
            Product(name='Xoài cát Hòa Lộc 1kg', description='Xoài cát Hòa Lộc ngọt ngào, thơm ngon', price=80000, category='Trái cây tươi', image_url='https://nongsandungha.com/wp-content/uploads/2024/07/xoai-cat-hoa-loc.png', stock=50),
            Product(name='Nho đen Ninh Thuận 500g', description='Nho đen không hạt từ Ninh Thuận', price=120000, category='Trái cây tươi', image_url='http://cntttest.vanlanguni.edu.vn:18080/k25-0102-team04/wp-content/uploads/2024/01/nho-keo-ninh-thuan-500g-202312141653351110.jpg', stock=40),
            Product(name='Dưa hấu ruột đỏ 3kg', description='Dưa hấu ngọt mát, ruột đỏ không hạt', price=60000, category='Trái cây tươi', image_url='https://salt.tikicdn.com/cache/w750/ts/product/68/9a/15/a5033e1e89896788a47153bd4fc2e6b5.jpg', stock=30),
            Product(name='Dứa Queen 1 trái', description='Dứa Queen thơm ngon, ngọt tự nhiên', price=45000, category='Trái cây tươi', image_url='https://xoaisaydeo.com/wp-content/uploads/2025/04/dua-qeen-3.jpg', stock=25),
            Product(name='Đu đủ Đức Trọng 1kg', description='Đu đủ chín vàng từ Đức Trọng, Lâm Đồng', price=35000, category='Trái cây tươi', image_url='http://banlandotbien.com/wp-content/uploads/2025/08/hat-giong-du-du-ruot-do-dai-loan-7.jpg', stock=45),
            Product(name='Bưởi da xanh 1 trái', description='Bưởi da xanh ngọt, múi căng tròn', price=80000, category='Trái cây tươi', image_url='https://chanhthu.com/wp-content/uploads/2024/03/chanh-thu-buoi-da-xanh-2.jpg', stock=20),
            Product(name='Chanh leo 1kg', description='Chanh leo chua ngọt, giàu vitamin C', price=55000, category='Trái cây tươi', image_url='https://cdn.tgdd.vn/2022/07/CookDish/chanh-day-la-gi-cac-loai-chanh-day-gia-bao-nhieu-1kg-va-lam-avt-1200x676-1.jpg', stock=60),
            # Rau củ quả (12 sản phẩm)
            Product(name='Rau muống 500g', description='Rau muống tươi xanh, an toàn không hóa chất', price=15000, category='Rau củ quả', image_url='https://shop.annam-gourmet.com/pub/media/catalog/product/i/t/item_F148433_8640.jpg', stock=40),
            Product(name='Cà rót 1kg', description='Cà rót tím tươi ngon, giàu vitamin', price=25000, category='Rau củ quả', image_url='https://khosifafood.vn/uploads/images/info/1kg-ca-rot-bao-nhieu-cu.png', stock=35),
            Product(name='Cà chua 1kg', description='Cà chua đỏ tươi, giàu lycopene tốt cho sức khỏe', price=20000, category='Rau củ quả', image_url='https://cdn.tgdd.vn/Products/Images/8785/271472/bhx/ca-chua-tui-1kg-10-12-trai-202205201608239644.jpg', stock=50),
            Product(name='Khoai tây Đà Lạt 1kg', description='Khoai tây Đà Lạt tươi ngon, thích hợp làm nhiều món', price=30000, category='Rau củ quả', image_url='https://thucphamnhanh.com/wp-content/uploads/2020/03/khoai-tay-bi-da-lat-loai-1kg-tuoi.jpg', stock=60),
            Product(name='Cải thảo 1kg', description='Cải thảo tươi ngon, lá xanh mướt', price=18000, category='Rau củ quả', image_url='https://greenseeds.net/wp-content/uploads/2021/05/bap-cai-thao-tui-1kg-202011131739445916.jpg', stock=45),
            Product(name='Củ cải trắng 1kg', description='Củ cải trắng tươi ngon, giòn ngọt', price=22000, category='Rau củ quả', image_url='https://cdn.tgdd.vn/Products/Images/8785/233985/bhx/cu-cai-trang-1kg-202207081346590565.jpg', stock=40),
            Product(name='Hành tây 500g', description='Hành tây tím ngọt, gia vị không thể thiếu', price=35000, category='Rau củ quả', image_url='https://cdn.tgdd.vn/Products/Images/8785/290836/bhx/hanh-tay-tui-500g-2-3-cu-202209141341034185.jpg', stock=70),
            Product(name='Tỏi 200g', description='Tỏi tươi thơm cay, tốt cho sức khỏe', price=45000, category='Rau củ quả', image_url='https://cdn.tgdd.vn/Products/Images/8820/271536/bhx/toi-co-don-tui-300g-202205190845024132.jpg', stock=80),
            Product(name='Ngô ngọt 3 trái', description='Ngô ngọt tươi, hạt căng tròn ngon ngọt', price=30000, category='Rau củ quả', image_url='http://www.vinaorganic.com/wp-content/uploads/2017/03/093323_ngo-ngot-2.jpg', stock=25),
            Product(name='Bí đỏ 1kg', description='Bí đỏ ngọt bùi, giàu beta-carotene', price=25000, category='Rau củ quả', image_url='https://cdn.tgdd.vn/Products/Images/8785/233887/bhx/bi-do-ho-lo-202312271411137609.jpg', stock=30),
            Product(name='Cần tây 300g', description='Cần tây tươi xanh, giòn ngọt thanh mát', price=20000, category='Rau củ quả', image_url='https://cdn.tgdd.vn/Products/Images/8820/233990/bhx/can-tay-1kg-202207051100301864.jpg', stock=35),
            Product(name='Su hào 1kg', description='Su hào tươi ngon, giòn ngọt và bổ dưỡng', price=28000, category='Rau củ quả', image_url='https://anvita.sgp1.cdn.digitaloceanspaces.com/ubofood/images/ubofood_560_420_37e1202c-ea84-4c09-8838-a23cec18ab9b.JPEG', stock=40),
            
            # Thực phẩm khô & Gia vị (15 sản phẩm)
            Product(name='Mì gói Hảo Hảo thùng 30 gói', description='Mì ăn liền vị tôm chua cay, thùng 30 gói tiện lợi', price=180000, category='Thực phẩm khô & Gia vị', image_url='https://product.hstatic.net/200000707089/product/thung-30-goi-mi-hao-hao-tom-chua-cay-75g-202211181144401243_a5aa7d764d4245508955afc92a1f3371.jpg', stock=80),
            Product(name='Dầu ăn Neptune 1L', description='Dầu ăn cao cấp từ đậu nành, tốt cho sức khỏe', price=65000, category='Thực phẩm khô & Gia vị', image_url='https://i.imgur.com/NQAoSBy.png', stock=70),
            Product(name='Nước mắm Phú Quốc 500ml', description='Nước mắm truyền thống Phú Quốc, độ đạm cao', price=85000, category='Thực phẩm khô & Gia vị', image_url='https://cdnv2.tgdd.vn/bhx-static/bhx/Products/Images/2289/112111/bhx/112111-slide-moii_202411041641243136.jpg', stock=60),
            Product(name='Đường cát trắng 1kg', description='Đường cát trắng tinh luyện, ngọt tự nhiên', price=25000, category='Thực phẩm khô & Gia vị', image_url='https://cdn.tgdd.vn/Products/Images/2804/229240/bhx/duong-cat-trang-co-tham-goi-1kg-202010171236114435.jpg', stock=90),
            Product(name='Muối biển 500g', description='Muối biển tự nhiên, tinh khiết không tẩy trắng', price=15000, category='Thực phẩm khô & Gia vị', image_url='https://tongkhogiavi.com.vn/upload/hinhanh/thumb/muoi-bien-bac-lieu-cao-cap-goi-500g9083.jpg', stock=100),
            Product(name='Tương ớt Chin-Su 270g', description='Tương ớt Chin-Su cay ngọt đậm đà', price=35000, category='Thực phẩm khô & Gia vị', image_url='http://product.hstatic.net/200000452921/product/tuong-ot-chinsu-chai-500g-201911011615532253_45de39623ecd4612ba834b620eca8e40_grande.jpg', stock=85),
            Product(name='Mì Chính Aji-nomoto 400g', description='Bột ngọt Aji-nomoto làm tăng hương vị món ăn', price=42000, category='Thực phẩm khô & Gia vị', image_url='https://bizweb.dktcdn.net/thumb/grande/100/469/765/products/11-3748a612-2629-4017-a875-e04bae7d859e.jpg', stock=75),
            Product(name='Bột nêm Knorr 900g', description='Bột nêm heo hầm xương Knorr thơm ngon', price=75000, category='Thực phẩm khô & Gia vị', image_url='https://cdnv2.tgdd.vn/bhx-static/bhx/Products/Images/2806/77241/bhx/77241-slide-moi_202409241043597461.jpg', stock=60),
            Product(name='Gạo tẻ thường 5kg', description='Gạo tẻ thường chất lượng tốt cho bữa cơm gia đình', price=120000, category='Thực phẩm khô & Gia vị', image_url='https://bizweb.dktcdn.net/thumb/grande/100/406/801/products/9-1200x676-ce53bad8-a37a-48d7-bd12-24a3bdda8df2.jpg?v=1632493134940', stock=50),
            Product(name='Mì spaghetti Barilla 500g', description='Mì Ý Barilla cao cấp nhập khẩu từ Italia', price=85000, category='Thực phẩm khô & Gia vị', image_url='https://cdn.tgdd.vn/Products/Images/8158/83052/bhx/mi-y-barilla-spaghetti-soi-500gam-2-700x467.jpg', stock=40),
            Product(name='Đậu phộng rang muối 500g', description='Đậu phộng rang muối giòn ngon, ăn vặt lý tưởng', price=45000, category='Thực phẩm khô & Gia vị', image_url='https://vn-test-11.slatic.net/shop/a0206a94e5dcc125a7c5ae66342af015.png', stock=65),
            Product(name='Nước tương Maggi 300ml', description='Nước tương đậm đà Maggi cho món xào', price=28000, category='Thực phẩm khô & Gia vị', image_url='https://cdnv2.tgdd.vn/bhx-static/bhx/Products/Images/2683/76547/bhx/nuoc-tuong-maggi-dam-dac-24-300ml_202509240928079925.jpg', stock=80),
            Product(name='Dầu mè 100ml', description='Dầu mè nguyên chất thơm béo, tăng hương vị', price=55000, category='Thực phẩm khô & Gia vị', image_url='https://cdn.tgdd.vn/Products/Images/2286/228302/bhx/dau-me-thom-tuong-an-chai-100ml-202407121521344497.jpg', stock=45),
            Product(name='Hạt nêm Gia Nguyên 200g', description='Hạt nêm tự nhiên từ xương heo và rau củ', price=32000, category='Thực phẩm khô & Gia vị', image_url='http://img.websosanh.vn/v2/users/wss/images/hat-nem-nam-huong-knorr-200g/n96zmhxuhogp5.jpg', stock=70),
            Product(name='Giấm táo Bragg 473ml', description='Giấm táo hữu cơ Bragg tốt cho sức khỏe', price=120000, category='Thực phẩm khô & Gia vị', image_url='https://product.hstatic.net/200000572551/product/ecafb00f-4790-42d8-88c7-b78ed5b6711f_9be2fe44c71043c1bb50633f0eaf3523_1024x1024.jpg', stock=30),
            
            # Đồ gia dụng nhà bếp (12 sản phẩm)
            Product(name='Nồi cơm điện Panasonic 1.8L', description='Nồi cơm điện cao cấp, nấu cơm ngon và tiết kiệm điện', price=1200000, category='Đồ gia dụng nhà bếp', image_url='https://s.meta.com.vn/Data/image/2022/08/15/noi-com-dien-co-1-8l-panasonic-sr-mvn18lrax-1.jpg', stock=25),
            Product(name='Máy xay sinh tố Philips', description='Máy xay sinh tố đa năng, công suất mạnh 600W', price=850000, category='Đồ gia dụng nhà bếp', image_url='https://bizweb.dktcdn.net/thumb/1024x1024/100/309/085/products/vlgjlb.png?v=1524489604593', stock=20),
            Product(name='Bộ dao nhà bếp 5 món', description='Bộ dao inox cao cấp gồm 5 món cơ bản cho nhà bếp', price=350000, category='Đồ gia dụng nhà bếp', image_url='https://konox.com.vn/wp-content/uploads/2024/08/bo-dao-lam-bep-5-mon-thep-duc-cao-cap-Konox-Impecca.jpg', stock=40),
            Product(name='Chảo chống dính 28cm', description='Chảo chống dính cao cấp, phù hợp cho mọi loại bếp', price=280000, category='Đồ gia dụng nhà bếp', image_url='https://cdn.tgdd.vn/Products/Images/2403/73580/do-dung-chao-tron-sunhouse-ct28-700x467-1.jpg', stock=30),
            Product(name='Máy pha cà phê Espresso', description='Máy pha cà phê espresso tự động, dễ sử dụng', price=2500000, category='Đồ gia dụng nhà bếp', image_url='https://vinbarista.com/uploads/news/nguyen-ly-hoat-dong-va-cau-tao-cua-may-pha-ca-phe-202407241530.jpg', stock=15),
            Product(name='Nồi áp suất 5L', description='Nồi áp suất inox 5L an toàn, nấu nhanh tiết kiệm gas', price=680000, category='Đồ gia dụng nhà bếp', image_url='https://kangaroo.vn/wp-content/uploads/2017/08/444_2311.jpg', stock=22),
            Product(name='Máy nướng bánh mì sandwich', description='Máy nướng bánh mì đa năng, 2 ngăn độc lập', price=450000, category='Đồ gia dụng nhà bếp', image_url='https://file.hstatic.net/200000836753/file/review-may-nuong-banh-mi-sandwich-1_11d7e32bada14d8eb4f31b1cc52b078b.jpg', stock=18),
            Product(name='Bộ nồi inox 304 cao cấp 5 món', description='Bộ nồi inox 304 bền đẹp, dùng mọi loại bếp', price=1200000, category='Đồ gia dụng nhà bếp', image_url='https://cdn1584.cdn4s4.io.vn/media/product/1168.jpg', stock=12),
            Product(name='Máy ép trái cây slow juicer', description='Máy ép chậm giữ nguyên vitamin và enzym', price=1800000, category='Đồ gia dụng nhà bếp', image_url='https://matika.vn/wp-content/uploads/2019/06/may-ep-cham-mtk3239-sang-trong-cung-vo-hop.jpg', stock=10),
            Product(name='Thớt gỗ cao su 35x25cm', description='Thớt gỗ cao su tự nhiên, kháng khuẩn an toàn', price=120000, category='Đồ gia dụng nhà bếp', image_url='https://thumbor.asia-southeast1.aeon-vn-prod.e.spresso.com/unsafe/fit-in/512x400/filters:quality(100):max_bytes(200000):fill(white)/https://catalog-assets-asia-southeast1.aeon-vn-prod.e.spresso.com/c3RvcmFnZS5nb29nbGVhcGlzLmNvbQ==/YWVvbnZpZXRuYW0tc3ByZXNzby1wdWJsaWM=/MjAyNQ==/SlVORQ==/MTA2MTMxNDYgKDIp.jpg', stock=50),
            Product(name='Máy đánh trứng cầm tay', description='Máy đánh trứng mini tiện lợi cho làm bánh', price=180000, category='Đồ gia dụng nhà bếp', image_url='https://file.hstatic.net/200000868155/file/7-post-top-10-loai-may-danh-trung-cam-tay-loai-nao-tot-nhat-hien-nay-1.jpg', stock=35),
            Product(name='Bình đựng nước thủy tinh 1.5L', description='Bình đựng nước thủy tinh cao cấp có nắp đậy', price=85000, category='Đồ gia dụng nhà bếp', image_url='https://cdn.tgdd.vn/Products/Images/4930/211767/binh-nuoc-thuy-tinh-borosilicate-co-tay-cam-15l-bh-1-700x467.jpg', stock=60),
            
            # Bánh kẹo & Snacks (10 sản phẩm)
            Product(name='Bánh Oreo gói lớn 274g', description='Bánh quy Oreo kem vani thơm ngon', price=45000, category='Bánh kẹo & Snacks', image_url='http://anhtuanbeerstore.mov.mn/files/sanpham/42/1/jpg/banh-cracker-dinh-duong-vi-lua-mi-afc-hop-100g.jpg', stock=80),
            Product(name='Kẹo Alpenliebe hũ 200 viên', description='Kẹo mềm Alpenliebe nhiều vị trái cây', price=65000, category='Bánh kẹo & Snacks', image_url='https://lookaside.instagram.com/seo/google_widget/crawler/?media_id=2396261205126120785', stock=50),
            Product(name='Khoai tây chiên Lay\'s 52g', description='Snack khoai tây chiên giòn tan nhiều vị', price=15000, category='Bánh kẹo & Snacks', image_url='https://pvmarthanoi.com.vn/wp-content/uploads/2022/12/snack-khoai-tay-vi-tu-nhien-poca-goi-52g-201911061622165483.jpg', stock=120),
            Product(name='Bánh quy dinh dưỡng Cosy 168g', description='Bánh quy ngũ cốc bổ dưỡng cho cả gia đình', price=35000, category='Bánh kẹo & Snacks', image_url='https://pos.nvncdn.com/bfafb3-133431/ps/20230720_e8vL2cBGV9.jpeg?v=1689869568', stock=70),
            Product(name='Chocolate Kitkat 4 thanh', description='Socola thanh Kitkat giòn tan thơm ngon', price=32000, category='Bánh kẹo & Snacks', image_url='http://cdn.hstatic.net/products/200000459373/socola_kitkat_thanh_4f_35g_f5bc79730e224a149823855a0f4adb1d_grande.jpg', stock=90),
            Product(name='Bánh tráng nướng Tây Ninh', description='Bánh tráng nướng đặc sản Tây Ninh thơm giòn', price=25000, category='Bánh kẹo & Snacks', image_url='https://mikiri.com.vn/wp-content/uploads/2024/12/banh-trang-nuong-ruoc-mikiri-9bb3e61e-ea7d-4c1f-9aaa-c61e0f244c25.jpg', stock=60),
            Product(name='Kẹo dẻo Haribo gấu 200g', description='Kẹo dẻo hình gấu Haribo ngọt ngào', price=55000, category='Bánh kẹo & Snacks', image_url='https://thucphamplaza.com/wp-content/uploads/products_img/keo-deo-haribo.jpg', stock=40),
            Product(name='Bánh xe đạp Kinh Đô hộp', description='Bánh quy bơ truyền thống Kinh Đô thơm ngon', price=85000, category='Bánh kẹo & Snacks', image_url='https://vongdap.com/wp-content/uploads/2022/12/kich-thuoc-banh-xe-dap-bia.jpg', stock=45),
            Product(name='Mứt dừa Bến Tre 200g', description='Mứt dừa non truyền thống Bến Tre ngọt dịu', price=35000, category='Bánh kẹo & Snacks', image_url='https://dacsanxudua.com/wp-content/uploads/2013/08/hop-mut-dua-sap-cocosweet-1200x800.jpg', stock=55),
            Product(name='Bánh mì sandwich đông lạnh 6 chiếc', description='Bánh mì sandwich tiện lợi, chỉ cần hâm nóng', price=120000, category='Bánh kẹo & Snacks', image_url='https://giadinh.mediacdn.vn/zoom/700_438/2019/8/2/0sandwich-food-lunch-snack-71916466-1564737139613695187961-crop-1564737166804221039311.jpg', stock=30),
            
            # Sản phẩm làm đẹp & Chăm sóc cá nhân (10 sản phẩm)
            Product(name='Dầu gội Clear Men 650ml', description='Dầu gội sạch gàu Clear Men cho nam giới', price=85000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://vn-test-11.slatic.net/p/44105487e6b4b32de780925ed2a2c6cb.jpg', stock=60),
            Product(name='Kem đánh răng P/S 240g', description='Kem đánh răng P/S bảo vệ nướu và men răng', price=25000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://lanchi.vn/wp-content/uploads/2021/11/KEM-DANH-RANG-PS-BAO-VE-123-TRA-XANH-240G.jpg', stock=100),
            Product(name='Sữa rửa mặt Cetaphil 125ml', description='Sữa rửa mặt dịu nhẹ cho da nhạy cảm', price=180000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://cdn.upharma.vn/unsafe/3840x0/filters:quality(90)/san-pham/10148.png', stock=40),
            Product(name='Dầu xả Sunsilk 650ml', description='Dầu xả Sunsilk nuôi dưỡng tóc mềm mượt', price=75000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://pvmarthanoi.com.vn/wp-content/uploads/2023/01/dau-xa-sunsilk-ong-muot-rang-ngoi-640g-202112151422500181.png', stock=50),
            Product(name='Sữa tắm Dove 530ml', description='Sữa tắm Dove dưỡng ẩm cho da mềm mại', price=95000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://tikicdn.com/media/catalog/product/d/e/deeply_530g_2.u2409.d20160823.t145455.25731.jpg', stock=70),
            Product(name='Kem chống nắng Nivea SPF50', description='Kem chống nắng Nivea bảo vệ da hiệu quả', price=120000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='http://file.hstatic.net/200000073977/article/feature_moi__b3add0df0be144f9a75811d3d1e2059c.jpg', stock=35),
            Product(name='Nước súc miệng Listerine 250ml', description='Nước súc miệng kháng khuẩn Listerine', price=65000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://cdn.upharma.vn/unsafe/3840x0/filters:quality(90)/san-pham/23158.png', stock=80),
            Product(name='Tăm bông Johnson 200 que', description='Tăm bông y tế Johnson an toàn và mềm mại', price=25000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://cdn.upharma.vn/unsafe/3840x0/filters:quality(90)/san-pham/22077.png', stock=90),
            Product(name='Khăn giấy ướt Bobby 80 tờ', description='Khăn giấy ướt kháng khuẩn cho bé và gia đình', price=35000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://cdn.tgdd.vn/Products/Images/3003/178264/bhx/khan-uot-em-be-bobby-khong-mui-goi-80-mieng-202202221610334050.jpg', stock=75),
            Product(name='Dầu dưỡng tóc Ellips 50 viên', description='Dầu dưỡng tóc dạng viên Ellips phục hồi tóc hư tổn', price=150000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://image.hsv-tech.io/1200x630/bbx/common/13cd35f5-bf74-4794-bd19-34c95b7dca69.webp', stock=25),
            
            # Đồ dùng gia đình (8 sản phẩm)
            Product(name='Giấy vệ sinh Tissue Paseo 12 cuộn', description='Giấy vệ sinh cao cấp mềm mại và thấm hút', price=65000, category='Đồ dùng gia đình', image_url='https://cdn.tgdd.vn/Products/Images/9081/114125/bhx/12-cuon-giay-ve-sinh-posy-economic-2-lop-202309260935490963.jpg', stock=100),
            Product(name='Nước giặt Ariel 2.4kg', description='Bột giặt Ariel giặt sạch và thơm lâu', price=180000, category='Đồ dùng gia đình', image_url='https://cdn.tgdd.vn/Products/Images/2464/210179/bhx/nuoc-giat-ariel-matic-cua-truoc-tuoi-mat-ruc-ro-tui-24kg-201912031338576015.jpg', stock=60),
            Product(name='Nước rửa chén Sunlight 750ml', description='Nước rửa chén Sunlight kháng khuẩn hiệu quả', price=45000, category='Đồ dùng gia đình', image_url='https://cdn.tgdd.vn/Products/Images/2387/76486/bhx/nuoc-rua-chen-sunlight-chiet-xuat-chanh-danh-bay-dau-mo-voi-suc-manh-nhu-100-trai-chanh-chai-725ml-202308231430517568.jpg', stock=80),
            Product(name='Túi rác đen 3 cuộn', description='Túi rác sinh học phân hủy thân thiện môi trường', price=35000, category='Đồ dùng gia đình', image_url='https://sieuthivmart.com.vn/wp-content/uploads/2021/10/loc-3-cuon-tui-rac-den-tu-huy-sinh-hoc-bach-hoa-xanh-64x78cm-1kg-202007291029379682.jpg', stock=120),
            Product(name='Nước lau sàn Vim 900ml', description='Nước lau sàn Vim khử mùi và kháng khuẩn', price=55000, category='Đồ dùng gia đình', image_url='https://cdn.tgdd.vn/Products/Images//2511/76924/bhx/files/2.jpg', stock=70),
            Product(name='Bàn chải cọ toilet', description='Bàn chải cọ vệ sinh toilet có tay cầm dài', price=25000, category='Đồ dùng gia đình', image_url='https://cdn.tgdd.vn//News/1512892//ban-chai-cha-san-nhua-15cm-tashuan-yj798-5-org-730x487.jpg', stock=50),
            Product(name='Khăn lau microfiber 5 chiếc', description='Bộ khăn lau microfiber đa năng thấm hút tốt', price=45000, category='Đồ dùng gia đình', image_url='https://hyperwork.vn/cdn/shop/files/11_11zon_11zon.jpg?v=1759942148&width=4000', stock=85),
            Product(name='Miếng rửa chén inox 10 chiếc', description='Miếng rửa chén inox bền bỉ không gỉ sét', price=15000, category='Đồ dùng gia đình', image_url='https://thietbivesinhviet.com/wp-content/uploads/2021/06/bon-rua-chen-inox-co-chan-mau.jpg', stock=150),
        ]
        
        for product in sample_products:
            db.session.add(product)
        db.session.commit()

# Tạo bảng khi khởi động app
with app.app_context():
    create_tables()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)