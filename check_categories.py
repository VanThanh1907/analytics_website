from app import app, db, Product

with app.app_context():
    print(f"Tổng số sản phẩm: {Product.query.count()}")
    print("\nDanh mục sản phẩm:")
    categories = db.session.query(
        Product.category, 
        db.func.count(Product.id)
    ).group_by(Product.category).all()
    
    for cat in categories:
        print(f"  {cat[0]}: {cat[1]} sản phẩm")