import os
import random
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ==========================================
# APPLICATION & DATABASE CONFIGURATION
# ==========================================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-secret-key-change-in-prod')

# Render uses 'DATABASE_URL', falls back to local SQLite if not found
db_url = os.environ.get('DATABASE_URL', 'sqlite:///biztrack.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==========================================
# EMAIL SMTP CONFIGURATION
# ==========================================
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False').lower() in ['true', '1']
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'True').lower() in ['true', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'joshola7073@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'vqrv uouf ecny oiui')

sender_email = app.config['MAIL_USERNAME']
app.config['MAIL_DEFAULT_SENDER'] = ('BizTrack', sender_email)

db = SQLAlchemy(app)
mail = Mail(app)

# ==========================================
# DATABASE MODELS
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', backref='owner', lazy=True, cascade="all, delete-orphan")
    sales = db.relationship('Sale', backref='owner', lazy=True, cascade="all, delete-orphan")
    expenses = db.relationship('Expense', backref='owner', lazy=True, cascade="all, delete-orphan")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    stock_qty = db.Column(db.Integer, default=0)
    sales_count = db.Column(db.Integer, default=0)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'total_amount': self.total_amount,
            'profit': self.profit,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
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

# ==========================================
# CONTEXT PROCESSOR & DECORATORS
# ==========================================

@app.context_processor
def inject_user():
    if 'user_id' in session:
        return {'current_user': User.query.get(session['user_id'])}
    return {'current_user': None}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# ROUTES & AUTHENTICATION
# ==========================================

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['business_name'] = user.business_name
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            if user.is_admin:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid email or password.")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        business_name = request.form.get('business_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if User.query.filter_by(email=email).first():
            return render_template('signup.html', error="An account with this email already exists.")

        hashed_pw = generate_password_hash(password)
        is_first_user = User.query.count() == 0
        is_admin = is_first_user or (email == os.environ.get('ADMIN_EMAIL', 'joshola7073@gmail.com').lower() or username.lower() == 'joshua')

        new_user = User(
            business_name=business_name,
            username=username,
            email=email,
            password_hash=hashed_pw,
            is_admin=is_admin
        )
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['email'] = new_user.email
        session['business_name'] = new_user.business_name
        session['username'] = new_user.username
        session['is_admin'] = new_user.is_admin

        return redirect(url_for('admin_panel' if is_admin else 'dashboard'))

    return render_template('signup.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            otp_code = str(random.randint(100000, 999999))
            
            session['reset_user_id'] = user.id
            session['reset_email'] = user.email
            session['reset_otp'] = otp_code

            print("\n" + "="*50)
            print(f" VERIFICATION CODE FOR {user.email}: {otp_code}")
            print("="*50 + "\n")

            try:
                msg = Message(
                    subject="BizTrack Password Reset Code",
                    sender=('BizTrack', app.config['MAIL_USERNAME']),
                    recipients=[user.email]
                )
                msg.body = f"Hello,\n\nYour verification code to reset your password on BizTrack is: {otp_code}\n\nIf you did not request this, please ignore this email."
                
                mail.send(msg)
                print(">>> Email successfully sent via Gmail SMTP! <<<")
                
            except Exception as e:
                print(f"\n[SMTP ERROR] Failed to dispatch mail: {e}\n")
                return render_template('forgot_password.html', error=f"Failed to send email. Check console error: {e}")

            return redirect(url_for('verify_code'))
        else:
            return render_template('forgot_password.html', error="No account found with that email address.")

    return render_template('forgot_password.html')

@app.route('/verify-code', methods=['GET', 'POST'])
def verify_code():
    if 'reset_user_id' not in session or 'reset_otp' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        user_code = (request.form.get('otp_code') or request.form.get('code') or '').strip()

        if user_code == session.get('reset_otp'):
            session['otp_verified'] = True
            return redirect(url_for('reset_password'))
        else:
            return render_template('verify_code.html', email=session.get('reset_email'), error="Invalid verification code. Please check your inbox and try again.")

    return render_template('verify_code.html', email=session.get('reset_email'))

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('otp_verified') or 'reset_user_id' not in session:
        return redirect(url_for('forgot_password'))

    user = User.query.get(session.get('reset_user_id'))
    
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if new_password != confirm_password:
            return render_template('reset_password.html', email=user.email, error="Passwords do not match.")

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        session.pop('reset_user_id', None)
        session.pop('reset_email', None)
        session.pop('reset_otp', None)
        session.pop('otp_verified', None)

        return render_template('login.html', success="Password reset successfully! Please log in with your new password.")

    return render_template('reset_password.html', email=user.email)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin_panel():
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_admin:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_panel'))

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.route('/api/summary', methods=['GET'])
@login_required
def get_summary():
    user_id = session['user_id']
    today = date.today()

    total_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(Sale.user_id == user_id).scalar() or 0.0
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(Expense.user_id == user_id).scalar() or 0.0

    today_sales_query = db.session.query(
        db.func.sum(Sale.total_amount),
        db.func.sum(Sale.profit)
    ).filter(Sale.user_id == user_id, db.func.date(Sale.created_at) == today).first()

    today_sales = today_sales_query[0] or 0.0
    today_profit = today_sales_query[1] or 0.0

    return jsonify({
        'expected_balance': total_sales - total_expenses,
        'today_sales': today_sales,
        'today_profit': today_profit,
        'total_sales': total_sales,
        'total_expenses': total_expenses
    })

@app.route('/api/products', methods=['GET', 'POST'])
@login_required
def handle_products():
    user_id = session['user_id']
    
    if request.method == 'POST':
        data = request.get_json()
        new_prod = Product(
            user_id=user_id,
            name=data['name'],
            cost_price=float(data['cost_price']),
            selling_price=float(data['selling_price']),
            stock_qty=int(data['stock_qty'])
        )
        db.session.add(new_prod)
        db.session.commit()
        return jsonify(new_prod.to_dict()), 201

    products = Product.query.filter_by(user_id=user_id).all()
    return jsonify([p.to_dict() for p in products])

@app.route('/api/products/<int:prod_id>/edit', methods=['PUT'])
@login_required
def edit_product(prod_id):
    prod = Product.query.filter_by(id=prod_id, user_id=session['user_id']).first_or_404()
    data = request.get_json()
    prod.cost_price = float(data['cost_price'])
    prod.selling_price = float(data['selling_price'])
    db.session.commit()
    return jsonify({'message': 'Product updated'})

@app.route('/api/products/<int:prod_id>/restock', methods=['POST'])
@login_required
def restock_product(prod_id):
    prod = Product.query.filter_by(id=prod_id, user_id=session['user_id']).first_or_404()
    data = request.get_json()
    prod.stock_qty += int(data['added_qty'])
    db.session.commit()
    return jsonify({'message': 'Stock updated'})

@app.route('/api/products/<int:prod_id>', methods=['DELETE'])
@login_required
def delete_product(prod_id):
    prod = Product.query.filter_by(id=prod_id, user_id=session['user_id']).first_or_404()
    db.session.delete(prod)
    db.session.commit()
    return jsonify({'message': 'Product deleted'})

@app.route('/api/sales', methods=['GET', 'POST'])
@login_required
def handle_sales():
    user_id = session['user_id']
    
    if request.method == 'POST':
        items = request.get_json()
        for item in items:
            prod = Product.query.filter_by(id=item['product_id'], user_id=user_id).first()
            if prod and prod.stock_qty >= item['quantity']:
                qty = item['quantity']
                total_amt = prod.selling_price * qty
                profit = (prod.selling_price - prod.cost_price) * qty
                
                prod.stock_qty -= qty
                prod.sales_count += qty

                new_sale = Sale(
                    user_id=user_id,
                    product_id=prod.id,
                    product_name=prod.name,
                    quantity=qty,
                    unit_price=prod.selling_price,
                    cost_price=prod.cost_price,
                    total_amount=total_amt,
                    profit=profit
                )
                db.session.add(new_sale)

        db.session.commit()
        return jsonify({'message': 'Sales recorded'}), 201

    sales = Sale.query.filter_by(user_id=user_id).order_by(Sale.created_at.desc()).all()
    return jsonify([s.to_dict() for s in sales])

@app.route('/api/expenses', methods=['GET', 'POST'])
@login_required
def handle_expenses():
    user_id = session['user_id']
    
    if request.method == 'POST':
        data = request.get_json()
        new_exp = Expense(
            user_id=user_id,
            title=data['title'],
            amount=float(data['amount'])
        )
        db.session.add(new_exp)
        db.session.commit()
        return jsonify(new_exp.to_dict()), 201

    expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.created_at.desc()).all()
    return jsonify([e.to_dict() for e in expenses])

@app.route('/api/daily-summary', methods=['GET'])
@login_required
def get_daily_summary():
    user_id = session['user_id']
    
    sales_by_day = db.session.query(
        db.func.date(Sale.created_at).label('day'),
        db.func.sum(Sale.total_amount).label('sales'),
        db.func.sum(Sale.profit).label('profit')
    ).filter(Sale.user_id == user_id).group_by('day').all()

    exp_by_day = dict(db.session.query(
        db.func.date(Expense.created_at).label('day'),
        db.func.sum(Expense.amount).label('expenses')
    ).filter(Expense.user_id == user_id).group_by('day').all())

    summary_dict = {}
    for row in sales_by_day:
        d = str(row.day)
        summary_dict[d] = {
            'date': d,
            'sales': row.sales or 0.0,
            'profit': row.profit or 0.0,
            'expenses': 0.0
        }

    for day_str, exp_sum in exp_by_day.items():
        d = str(day_str)
        if d not in summary_dict:
            summary_dict[d] = {'date': d, 'sales': 0.0, 'profit': 0.0, 'expenses': exp_sum or 0.0}
        else:
            summary_dict[d]['expenses'] = exp_sum or 0.0

    result = []
    for d, val in sorted(summary_dict.items(), reverse=True):
        val['net_cash'] = val['profit'] - val['expenses']
        result.append(val)

    return jsonify(result)

@app.route('/api/reset', methods=['POST'])
@login_required
@admin_required
def reset_system():
    data = request.get_json() or {}
    reset_type = data.get('type', 'transactions')

    Sale.query.delete()
    Expense.query.delete()

    if reset_type == 'full':
        Product.query.delete()
    else:
        products = Product.query.all()
        for p in products:
            p.sales_count = 0

    db.session.commit()
    return jsonify({'message': 'System reset completed successfully'})

# ==========================================
# DB INITIALIZATION & SEEDING
# ==========================================

def init_db():
    with app.app_context():
        db.create_all()
        
        admin_email = os.environ.get('ADMIN_EMAIL', 'joshola7073@gmail.com')
        admin_pass = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin_user = User.query.filter(db.func.lower(User.email) == admin_email.lower()).first()
        
        if not admin_user:
            try:
                default_admin = User(
                    business_name="BizTrack Admin Console",
                    username="joshua",
                    email=admin_email,
                    password_hash=generate_password_hash(admin_pass),
                    is_admin=True
                )
                db.session.add(default_admin)
                db.session.commit()
                print(f"--> Seeded default admin user: '{admin_email}'")
            except Exception as e:
                db.session.rollback()
                print(f"--> Admin user failed to seed: {e}")

init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)