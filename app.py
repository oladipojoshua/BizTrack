import os

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

# Configure SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tife_hair.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create an absolute path to the database in the app folder
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'tife_hair.db')
db = SQLAlchemy(app)

# -------------------------------------------------------------------
# DATABASE MODELS
# -------------------------------------------------------------------

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    sales_count = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cost_price': self.cost_price,
            'selling_price': self.selling_price,
            'stock_qty': self.stock_qty,
            'sales_count': self.sales_count
        }

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'selling_price': self.selling_price,
            'total_amount': self.total_amount,
            'profit': self.profit,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'amount': self.amount,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

# Initialize Database Tables
with app.app_context():
    db.create_all()

# -------------------------------------------------------------------
# ROUTES & API ENDPOINTS
# -------------------------------------------------------------------

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/daily-summary', methods=['GET'])
def get_daily_summary():
    daily_data = defaultdict(lambda: {'sales': 0.0, 'profit': 0.0, 'expenses': 0.0})

    # Aggregate Sales by Date
    for sale in Sale.query.all():
        date_str = sale.created_at.strftime('%Y-%m-%d')
        daily_data[date_str]['sales'] += sale.total_amount
        daily_data[date_str]['profit'] += sale.profit

    # Aggregate Expenses by Date
    for exp in Expense.query.all():
        date_str = exp.created_at.strftime('%Y-%m-%d')
        daily_data[date_str]['expenses'] += exp.amount

    # Convert to sorted list (latest date first)
    summary_list = []
    for date_str in sorted(daily_data.keys(), reverse=True):
        data = daily_data[date_str]
        summary_list.append({
            'date': date_str,
            'sales': data['sales'],
            'profit': data['profit'],
            'expenses': data['expenses'],
            'net_cash': data['sales'] - data['expenses']
        })

    return jsonify(summary_list)

# --- Products API ---

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    new_prod = Product(
        name=data['name'],
        cost_price=float(data['cost_price']),
        selling_price=float(data['selling_price']),
        stock_qty=int(data['stock_qty'])
    )
    db.session.add(new_prod)
    db.session.commit()
    return jsonify({'message': 'Product added successfully', 'product': new_prod.to_dict()})

@app.route('/api/products/<int:prod_id>/restock', methods=['POST'])
def restock_product(prod_id):
    data = request.get_json()
    product = Product.query.get_or_404(prod_id)
    product.stock_qty += int(data['added_qty'])
    db.session.commit()
    return jsonify({'message': 'Stock updated', 'product': product.to_dict()})

@app.route('/api/products/<int:prod_id>', methods=['DELETE'])
def delete_product(prod_id):
    product = Product.query.get_or_404(prod_id) # cite: 1.1.2
    db.session.delete(product) # cite: 1.1.2
    db.session.commit() # cite: 1.1.2
    return jsonify({'message': 'Product deleted successfully'})

@app.route('/api/products/<int:prod_id>/edit', methods=['PUT'])
def edit_product(prod_id):
    product = Product.query.get_or_404(prod_id)
    data = request.get_json()
    
    product.cost_price = float(data['cost_price'])
    product.selling_price = float(data['selling_price'])
    
    db.session.commit()
    return jsonify({'message': 'Product prices updated successfully', 'product': product.to_dict()})

# --- Sales API ---

@app.route('/api/sales', methods=['GET'])
def get_sales():
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    return jsonify([s.to_dict() for s in sales])

@app.route('/api/sales', methods=['POST'])
def record_sales():
    items = request.get_json()  # List of items sold: [{product_id, quantity}, ...]
    recorded_sales = []

    for item in items:
        product = Product.query.get(item['product_id'])
        if product and product.stock_qty >= item['quantity']:
            qty = item['quantity']
            total = product.selling_price * qty
            profit = (product.selling_price - product.cost_price) * qty

            # Deduct stock and increment sales count
            product.stock_qty -= qty
            product.sales_count += qty

            # Record transaction
            sale = Sale(
                product_id=product.id,
                product_name=product.name,
                quantity=qty,
                selling_price=product.selling_price,
                cost_price=product.cost_price,
                total_amount=total,
                profit=profit
            )
            db.session.add(sale)
            recorded_sales.append(sale)

    db.session.commit()
    return jsonify({'message': f'Recorded {len(recorded_sales)} sales successfully'})

# --- Expenses API ---

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    return jsonify([e.to_dict() for e in expenses])

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    new_exp = Expense(
        title=data['title'],
        amount=float(data['amount'])
    )
    db.session.add(new_exp)
    db.session.commit()
    return jsonify({'message': 'Expense logged successfully', 'expense': new_exp.to_dict()})

# --- Metrics Summary API ---

@app.route('/api/summary', methods=['GET'])
def get_summary():
    products = Product.query.all()
    sales = Sale.query.all()
    expenses = Expense.query.all()

    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    total_sales = sum(s.total_amount for s in sales)
    total_profit = sum(s.profit for s in sales)
    total_expenses = sum(e.amount for e in expenses)

    today_sales = sum(s.total_amount for s in sales if s.created_at.strftime('%Y-%m-%d') == today_str)
    today_profit = sum(s.profit for s in sales if s.created_at.strftime('%Y-%m-%d') == today_str)

    expected_balance = total_sales - total_expenses

    return jsonify({
        'total_sales': total_sales,
        'total_profit': total_profit,
        'today_sales': today_sales,
        'today_profit': today_profit,
        'total_expenses': total_expenses,
        'expected_balance': expected_balance
    })

@app.route('/api/reset', methods=['POST'])
def reset_system():
    data = request.get_json() or {}
    reset_type = data.get('type', 'transactions')  # 'transactions' or 'full'

    # 1. Clear Sales and Expense Records
    Sale.query.delete()
    Expense.query.delete()

    # 2. If Full Reset, clear Products and reset sales counters
    if reset_type == 'full':
        Product.query.delete()
    else:
        # Reset sales_count on existing products back to 0
        products = Product.query.all()
        for p in products:
            p.sales_count = 0

    db.session.commit()
    return jsonify({'message': 'System reset completed successfully'})

if __name__ == '__main__':
    app.run(debug=True)