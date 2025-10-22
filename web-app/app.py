from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from kafka import KafkaProducer
import json
import redis
import os
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

# Routes
@app.route('/')
def index():
    # Tạo session ID nếu chưa có
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
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
            send_user_event(user.id, 'login', {'username': username})
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

@app.route('/api/track_click', methods=['POST'])
def track_click():
    data = request.get_json()
    
    if current_user.is_authenticated:
        send_user_event(current_user.id, 'click', data)
        
        # Lưu vào database nếu là click vào sản phẩm
        if data.get('product_id'):
            interaction = UserInteraction(
                user_id=current_user.id,
                product_id=data.get('product_id'),
                interaction_type='click',
                details=data
            )
            db.session.add(interaction)
            db.session.commit()
    
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
    api_result = call_recommendation_api('recommendations', current_user.id, num_recs=6)
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
    
    # Fallback: try direct API if available
    elif recommendation_api:
        try:
            print("🔄 Trying direct recommendation engine...")
            result = recommendation_api.get_recommendations_for_user(current_user.id, 6)
            if result['status'] == 'success' and result['recommendations']:
                product_ids = [p['id'] for p in result['recommendations']]
                if product_ids:
                    recommendations = Product.query.filter(Product.id.in_(product_ids)).all()
                    recommendations_dict = {p.id: p for p in recommendations}
                    recommendations = [recommendations_dict[pid] for pid in product_ids if pid in recommendations_dict]
                    analysis_data = result.get('analysis', {})
                    print(f"✅ Direct engine recommendations: {len(recommendations)} sản phẩm")
        except Exception as e:
            print(f"❌ Lỗi direct recommendation engine: {e}")
    
    # NO MORE RANDOM FALLBACK - Chỉ dựa vào Kafka data
    if not recommendations:
        print("⚠️ Không có dữ liệu Kafka - không có gợi ý")
        analysis_data = {
            'strategy_used': 'no_kafka_data',
            'note': 'Chưa có dữ liệu hành vi từ Kafka. Hãy click vào sản phẩm để hệ thống học sở thích của bạn!'
        }
    
    # Debug log
    print(f"🎯 Final strategy: {analysis_data.get('strategy_used', 'unknown')}")
    print(f"📦 Recommendations count: {len(recommendations)}")
    
    # Gửi event xem trang recommendations
    send_user_event(current_user.id, 'recommendations_view', {
        'recommendation_count': len(recommendations),
        'strategy_used': analysis_data.get('strategy_used', 'unknown'),
        'has_behavior_data': analysis_data.get('total_interactions', 0) > 0,
        'api_used': 'server' if api_result else ('direct' if recommendation_api else 'none')
    })
    
    return render_template('recommendations.html', 
                         products=recommendations, 
                         analysis=analysis_data)

@app.route('/category/<category>')
def category_products(category):
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
    # Lấy danh sách tất cả danh mục và số lượng sản phẩm
    categories_data = db.session.query(
        Product.category, 
        db.func.count(Product.id).label('count')
    ).group_by(Product.category).all()
    
    return render_template('categories.html', categories=categories_data)

# Import recommendation API
import sys
import os
import requests

# Try to use local API server
RECOMMENDATION_API_URL = os.getenv('RECOMMENDATION_API_URL', 'http://localhost:5002')  # Changed to port 5002

def call_recommendation_api(endpoint, user_id=None, **kwargs):
    """Call recommendation API server"""
    try:
        if user_id:
            url = f"{RECOMMENDATION_API_URL}/{endpoint}/{user_id}"
        else:
            url = f"{RECOMMENDATION_API_URL}/{endpoint}"
        
        print(f"🌐 Calling API: {url}")
        response = requests.get(url, params=kwargs, timeout=5)
        print(f"📞 API response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        print(f"📊 API response data: {result}")
        return result
    except Exception as e:
        print(f"❌ Lỗi gọi recommendation API: {e}")
        return None

# Fallback: try to import direct
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'recommendation-engine'))

try:
    from recommendation_api import RecommendationAPI
    recommendation_api = RecommendationAPI()
    print("✅ Direct recommendation engine loaded")
except ImportError:
    recommendation_api = None
    print("⚠️ Using API server for recommendations")

# Khởi tạo database
def create_tables():
    db.create_all()
    
    # Tạo dữ liệu mẫu nếu chưa có
    if Product.query.count() == 0:
        sample_products = [
            # Thực phẩm tươi sống (15 sản phẩm)
            Product(name='Gạo ST25 túi 5kg', description='Gạo thơm ngon, chất lượng cao từ An Giang', price=180000, category='Thực phẩm tươi sống', image_url='https://tse3.mm.bing.net/th/id/OIP.tiXbm0NPSwS5vHgDN13s9wHaHa?pid=Api&P=0&h=180', stock=100),
            Product(name='Thịt heo ba chỉ 1kg', description='Thịt heo tươi ngon, đảm bảo vệ sinh an toàn thực phẩm', price=180000, category='Thực phẩm tươi sống', image_url='https://tse3.mm.bing.net/th/id/OIP.tiXbm0NPSwS5vHgDN13s9wHaHa?pid=Api&P=0&h=180', stock=30),
            Product(name='Thịt bò úc 500g', description='Thịt bò nhập khẩu từ Úc, thịt thăn mềm ngon', price=350000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1603048297172-c92544798d5a?w=400', stock=25),
            Product(name='Cá hồi Na Uy 1kg', description='Cá hồi tươi ngon nhập khẩu từ Na Uy', price=450000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400', stock=20),
            Product(name='Tôm sú 500g', description='Tôm sú tươi ngon từ vùng nuôi sạch Cần Thơ', price=280000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1615141982883-c7ad0e69fd62?w=400', stock=40),
            Product(name='Thịt gà ta 1kg', description='Thịt gà ta thả vườn, tự nhiên không hormone', price=120000, category='Thực phẩm tươi sống', image_url='https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?w=400', stock=35),
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
            Product(name='Coca Cola lon 330ml (24 lon)', description='Nước ngọt có ga vị cola truyền thống', price=360000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=400', stock=50),
            Product(name='Sữa tươi TH True Milk 1L', description='Sữa tươi nguyên chất 100%, giàu canxi và protein', price=32000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1563636619-e9143da7973b?w=400', stock=80),
            Product(name='Trà xanh Thái Nguyên 500g', description='Trà xanh cao cấp từ Thái Nguyên, thơm ngon', price=180000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400', stock=45),
            Product(name='Cà phê Arabica Buôn Ma Thuột 500g', description='Cà phê rang xay nguyên chất từ Buôn Ma Thuột', price=220000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400', stock=55),
            Product(name='Nước cam ép tươi 1L', description='Nước cam ép tươi 100%, không chất bảo quản', price=45000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400', stock=65),
            Product(name='Pepsi lon 330ml (24 lon)', description='Nước ngọt có ga Pepsi thùng 24 lon', price=340000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1520342868574-5fa3804e551c?w=400', stock=45),
            Product(name='Sting năng lượng (24 lon)', description='Nước tăng lực Sting thùng 24 lon', price=480000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=400', stock=40),
            Product(name='Nước suối Lavie 500ml (24 chai)', description='Nước suối tinh khiết Lavie thùng 24 chai', price=120000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1560089168-6516081f5bf1?w=400', stock=100),
            Product(name='Trà sữa hòa tan Lipton 20 gói', description='Trà sữa hòa tan tiện lợi, vị thơm ngon', price=85000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1571091655789-405eb7a3a3a8?w=400', stock=70),
            Product(name='Nước dừa xiêm 500ml (12 chai)', description='Nước dừa xiêm tự nhiên, mát lành', price=180000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400', stock=35),
            Product(name='Sữa chua uống TH True Yogurt', description='Sữa chua uống có lợi khuẩn, nhiều vị', price=25000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1571212515416-fae2e5c5ca3c?w=400', stock=90),
            Product(name='Nước ngọt 7Up lon 330ml (24 lon)', description='Nước ngọt có ga 7Up thùng 24 lon', price=350000, category='Đồ uống & Nước giải khát', image_url='https://images.unsplash.com/photo-1622543925917-763c34d1a86e?w=400', stock=40),
            
            # Trái cây tươi (10 sản phẩm)
            Product(name='Táo Fuji Nhật Bản 1kg', description='Táo Fuji nhập khẩu từ Nhật Bản, ngọt giòn', price=120000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=400', stock=60),
            Product(name='Chuối già Nam Mỹ 1kg', description='Chuối chín vàng, ngọt và bổ dưỡng', price=35000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1481349518771-20055b2a7b24?w=400', stock=90),
            Product(name='Cam sành Cao Phong 1kg', description='Cam sành tươi ngon từ Cao Phong, Hòa Bình', price=45000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1580052614034-c55d20bfee3b?w=400', stock=70),
            Product(name='Xoài cát Hòa Lộc 1kg', description='Xoài cát Hòa Lộc ngọt ngào, thơm ngon', price=80000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1553279768-865429ffd9d1?w=400', stock=50),
            Product(name='Nho đen Ninh Thuận 500g', description='Nho đen không hạt từ Ninh Thuận', price=120000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1537640538966-79f369143715?w=400', stock=40),
            Product(name='Dưa hấu ruột đỏ 3kg', description='Dưa hấu ngọt mát, ruột đỏ không hạt', price=60000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1563114773-84221bd62daa?w=400', stock=30),
            Product(name='Dứa Queen 1 trái', description='Dứa Queen thơm ngon, ngọt tự nhiên', price=45000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1550258987-190a2d41a8ba?w=400', stock=25),
            Product(name='Đu đủ Đức Trọng 1kg', description='Đu đủ chín vàng từ Đức Trọng, Lâm Đồng', price=35000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1583663238203-68ad6e5e5be4?w=400', stock=45),
            Product(name='Bưởi da xanh 1 trái', description='Bưởi da xanh ngọt, múi căng tròn', price=80000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400', stock=20),
            Product(name='Chanh leo 1kg', description='Chanh leo chua ngọt, giàu vitamin C', price=55000, category='Trái cây tươi', image_url='https://images.unsplash.com/photo-1587735243249-98764e80d1ae?w=400', stock=60),
            
            # Rau củ quả (12 sản phẩm)
            Product(name='Rau muống 500g', description='Rau muống tươi xanh, an toàn không hóa chất', price=15000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=400', stock=40),
            Product(name='Cà rót 1kg', description='Cà rót tím tươi ngon, giàu vitamin', price=25000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1659261200833-ec8761558cd7?w=400', stock=35),
            Product(name='Cà chua 1kg', description='Cà chua đỏ tươi, giàu lycopene tốt cho sức khỏe', price=20000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1558818498-28c1e002b655?w=400', stock=50),
            Product(name='Khoai tây Đà Lạt 1kg', description='Khoai tây Đà Lạt tươi ngon, thích hợp làm nhiều món', price=30000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400', stock=60),
            Product(name='Cải thảo 1kg', description='Cải thảo tươi ngon, lá xanh mướt', price=18000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1518962443565-1cbc004d9532?w=400', stock=45),
            Product(name='Củ cải trắng 1kg', description='Củ cải trắng tươi ngon, giòn ngọt', price=22000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1589927986089-35812378d999?w=400', stock=40),
            Product(name='Hành tây 500g', description='Hành tây tím ngọt, gia vị không thể thiếu', price=35000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400', stock=70),
            Product(name='Tỏi 200g', description='Tỏi tươi thơm cay, tốt cho sức khỏe', price=45000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1553944147-6e04ce42f37b?w=400', stock=80),
            Product(name='Ngô ngọt 3 trái', description='Ngô ngọt tươi, hạt căng tròn ngon ngọt', price=30000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=400', stock=25),
            Product(name='Bí đỏ 1kg', description='Bí đỏ ngọt bùi, giàu beta-carotene', price=25000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=400', stock=30),
            Product(name='Cần tây 300g', description='Cần tây tươi xanh, giòn ngọt thanh mát', price=20000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1574316071802-0d684efa7bf5?w=400', stock=35),
            Product(name='Su hào 1kg', description='Su hào tươi ngon, giòn ngọt và bổ dưỡng', price=28000, category='Rau củ quả', image_url='https://images.unsplash.com/photo-1594736797933-d0a9a5039cd6?w=400', stock=40),
            
            # Thực phẩm khô & Gia vị (15 sản phẩm)
            Product(name='Mì gói Hảo Hảo thùng 30 gói', description='Mì ăn liền vị tôm chua cay, thùng 30 gói tiện lợi', price=180000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400', stock=80),
            Product(name='Dầu ăn Neptune 1L', description='Dầu ăn cao cấp từ đậu nành, tốt cho sức khỏe', price=65000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400', stock=70),
            Product(name='Nước mắm Phú Quốc 500ml', description='Nước mắm truyền thống Phú Quốc, độ đạm cao', price=85000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=60),
            Product(name='Đường cát trắng 1kg', description='Đường cát trắng tinh luyện, ngọt tự nhiên', price=25000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400', stock=90),
            Product(name='Muối biển 500g', description='Muối biển tự nhiên, tinh khiết không tẩy trắng', price=15000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=100),
            Product(name='Tương ớt Chin-Su 270g', description='Tương ớt Chin-Su cay ngọt đậm đà', price=35000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=85),
            Product(name='Mì Chính Aji-nomoto 400g', description='Bột ngọt Aji-nomoto làm tăng hương vị món ăn', price=42000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=75),
            Product(name='Bột nêm Knorr 900g', description='Bột nêm heo hầm xương Knorr thơm ngon', price=75000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=60),
            Product(name='Gạo tẻ thường 5kg', description='Gạo tẻ thường chất lượng tốt cho bữa cơm gia đình', price=120000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400', stock=50),
            Product(name='Mì spaghetti Barilla 500g', description='Mì Ý Barilla cao cấp nhập khẩu từ Italia', price=85000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1551892374-ecf8db2090fe?w=400', stock=40),
            Product(name='Đậu phộng rang muối 500g', description='Đậu phộng rang muối giòn ngon, ăn vặt lý tưởng', price=45000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1582058091505-f87a2e55a40f?w=400', stock=65),
            Product(name='Nước tương Maggi 300ml', description='Nước tương đậm đà Maggi cho món xào', price=28000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=80),
            Product(name='Dầu mè 100ml', description='Dầu mè nguyên chất thơm béo, tăng hương vị', price=55000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400', stock=45),
            Product(name='Hạt nêm Gia Nguyên 200g', description='Hạt nêm tự nhiên từ xương heo và rau củ', price=32000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=70),
            Product(name='Giấm táo Bragg 473ml', description='Giấm táo hữu cơ Bragg tốt cho sức khỏe', price=120000, category='Thực phẩm khô & Gia vị', image_url='https://images.unsplash.com/photo-1599909533269-1094718b0c90?w=400', stock=30),
            
            # Đồ gia dụng nhà bếp (12 sản phẩm)
            Product(name='Nồi cơm điện Panasonic 1.8L', description='Nồi cơm điện cao cấp, nấu cơm ngon và tiết kiệm điện', price=1200000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', stock=25),
            Product(name='Máy xay sinh tố Philips', description='Máy xay sinh tố đa năng, công suất mạnh 600W', price=850000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=400', stock=20),
            Product(name='Bộ dao nhà bếp 5 món', description='Bộ dao inox cao cấp gồm 5 món cơ bản cho nhà bếp', price=350000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1593618998160-e34014e67546?w=400', stock=40),
            Product(name='Chảo chống dính 28cm', description='Chảo chống dính cao cấp, phù hợp cho mọi loại bếp', price=280000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', stock=30),
            Product(name='Máy pha cà phê Espresso', description='Máy pha cà phê espresso tự động, dễ sử dụng', price=2500000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400', stock=15),
            Product(name='Nồi áp suất 5L', description='Nồi áp suất inox 5L an toàn, nấu nhanh tiết kiệm gas', price=680000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', stock=22),
            Product(name='Máy nướng bánh mì sandwich', description='Máy nướng bánh mì đa năng, 2 ngăn độc lập', price=450000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', stock=18),
            Product(name='Bộ nồi inox 304 cao cấp 5 món', description='Bộ nồi inox 304 bền đẹp, dùng mọi loại bếp', price=1200000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', stock=12),
            Product(name='Máy ép trái cây slow juicer', description='Máy ép chậm giữ nguyên vitamin và enzym', price=1800000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=400', stock=10),
            Product(name='Thớt gỗ cao su 35x25cm', description='Thớt gỗ cao su tự nhiên, kháng khuẩn an toàn', price=120000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1593618998160-e34014e67546?w=400', stock=50),
            Product(name='Máy đánh trứng cầm tay', description='Máy đánh trứng mini tiện lợi cho làm bánh', price=180000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', stock=35),
            Product(name='Bình đựng nước thủy tinh 1.5L', description='Bình đựng nước thủy tinh cao cấp có nắp đậy', price=85000, category='Đồ gia dụng nhà bếp', image_url='https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', stock=60),
            
            # Bánh kẹo & Snacks (10 sản phẩm)
            Product(name='Bánh Oreo gói lớn 274g', description='Bánh quy Oreo kem vani thơm ngon', price=45000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400', stock=80),
            Product(name='Kẹo Alpenliebe hũ 200 viên', description='Kẹo mềm Alpenliebe nhiều vị trái cây', price=65000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1582058091505-f87a2e55a40f?w=400', stock=50),
            Product(name='Khoai tây chiên Lay\'s 52g', description='Snack khoai tây chiên giòn tan nhiều vị', price=15000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=400', stock=120),
            Product(name='Bánh quy dinh dưỡng Cosy 168g', description='Bánh quy ngũ cốc bổ dưỡng cho cả gia đình', price=35000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1548586744-7e9707109650?w=400', stock=70),
            Product(name='Chocolate Kitkat 4 thanh', description='Socola thanh Kitkat giòn tan thơm ngon', price=32000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1511381939415-e44015466834?w=400', stock=90),
            Product(name='Bánh tráng nướng Tây Ninh', description='Bánh tráng nướng đặc sản Tây Ninh thơm giòn', price=25000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1548586744-7e9707109650?w=400', stock=60),
            Product(name='Kẹo dẻo Haribo gấu 200g', description='Kẹo dẻo hình gấu Haribo ngọt ngào', price=55000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1582058091505-f87a2e55a40f?w=400', stock=40),
            Product(name='Bánh xe đạp Kinh Đô hộp', description='Bánh quy bơ truyền thống Kinh Đô thơm ngon', price=85000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1548586744-7e9707109650?w=400', stock=45),
            Product(name='Mứt dừa Bến Tre 200g', description='Mứt dừa non truyền thống Bến Tre ngọt dịu', price=35000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1582058091505-f87a2e55a40f?w=400', stock=55),
            Product(name='Bánh mì sandwich đông lạnh 6 chiếc', description='Bánh mì sandwich tiện lợi, chỉ cần hâm nóng', price=120000, category='Bánh kẹo & Snacks', image_url='https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400', stock=30),
            
            # Sản phẩm làm đẹp & Chăm sóc cá nhân (10 sản phẩm)
            Product(name='Dầu gội Clear Men 650ml', description='Dầu gội sạch gàu Clear Men cho nam giới', price=85000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=60),
            Product(name='Kem đánh răng P/S 240g', description='Kem đánh răng P/S bảo vệ nướu và men răng', price=25000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=100),
            Product(name='Sữa rửa mặt Cetaphil 125ml', description='Sữa rửa mặt dịu nhẹ cho da nhạy cảm', price=180000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=40),
            Product(name='Dầu xả Sunsilk 650ml', description='Dầu xả Sunsilk nuôi dưỡng tóc mềm mượt', price=75000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=50),
            Product(name='Sữa tắm Dove 530ml', description='Sữa tắm Dove dưỡng ẩm cho da mềm mại', price=95000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=70),
            Product(name='Kem chống nắng Nivea SPF50', description='Kem chống nắng Nivea bảo vệ da hiệu quả', price=120000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=35),
            Product(name='Nước súc miệng Listerine 250ml', description='Nước súc miệng kháng khuẩn Listerine', price=65000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=80),
            Product(name='Tăm bông Johnson 200 que', description='Tăm bông y tế Johnson an toàn và mềm mại', price=25000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=90),
            Product(name='Khăn giấy ướt Bobby 80 tờ', description='Khăn giấy ướt kháng khuẩn cho bé và gia đình', price=35000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=75),
            Product(name='Dầu dưỡng tóc Ellips 50 viên', description='Dầu dưỡng tóc dạng viên Ellips phục hồi tóc hư tổn', price=150000, category='Sản phẩm làm đẹp & Chăm sóc cá nhân', image_url='https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400', stock=25),
            
            # Đồ dùng gia đình (8 sản phẩm)
            Product(name='Giấy vệ sinh Tissue Paseo 12 cuộn', description='Giấy vệ sinh cao cấp mềm mại và thấm hút', price=65000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=100),
            Product(name='Nước giặt Ariel 2.4kg', description='Bột giặt Ariel giặt sạch và thơm lâu', price=180000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=60),
            Product(name='Nước rửa chén Sunlight 750ml', description='Nước rửa chén Sunlight kháng khuẩn hiệu quả', price=45000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=80),
            Product(name='Túi rác đen 3 cuộn', description='Túi rác sinh học phân hủy thân thiện môi trường', price=35000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=120),
            Product(name='Nước lau sàn Vim 900ml', description='Nước lau sàn Vim khử mùi và kháng khuẩn', price=55000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=70),
            Product(name='Bàn chải cọ toilet', description='Bàn chải cọ vệ sinh toilet có tay cầm dài', price=25000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=50),
            Product(name='Khăn lau microfiber 5 chiếc', description='Bộ khăn lau microfiber đa năng thấm hút tốt', price=45000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=85),
            Product(name='Miếng rửa chén inox 10 chiếc', description='Miếng rửa chén inox bền bỉ không gỉ sét', price=15000, category='Đồ dùng gia đình', image_url='https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400', stock=150),
        ]
        
        for product in sample_products:
            db.session.add(product)
        db.session.commit()

# Tạo bảng khi khởi động app
with app.app_context():
    create_tables()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)