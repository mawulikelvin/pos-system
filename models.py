from extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# User & Roles
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Enum("admin", "cashier", "staff", name="user_roles"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    sales = db.relationship('Sale', backref='cashier', lazy=True)
    stock_adjustments = db.relationship('StockAdjustment', backref='created_by_user', lazy=True)
    purchase_orders = db.relationship('PurchaseOrder', backref='created_by_user', lazy=True)
    activity_logs = db.relationship('UserActivityLog', backref='user', lazy=True)
    
    @property
    def is_active(self):
        # Consider users with 'staff' role as inactive (deactivated)
        return self.role in ['admin', 'cashier']
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Inventory
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(50), unique=True)
    category = db.Column(db.String(50))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float)
    stock_quantity = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=5)
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='product', lazy=True)
    stock_adjustments = db.relationship('StockAdjustment', backref='product', lazy=True)
    purchase_items = db.relationship('PurchaseItem', backref='product', lazy=True)

class StockAdjustment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    adjustment_type = db.Column(db.Enum("damage", "return", "manual", name="adjustment_types"))
    quantity = db.Column(db.Integer)
    note = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Sales
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cashier_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    total_amount = db.Column(db.Float)
    discount_amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.Enum("cash", "card", "mobile_money", "split", name="payment_methods"))
    status = db.Column(db.Enum("completed", "on_hold", "refunded", name="sale_status"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    receipt = db.relationship('Receipt', backref='sale', lazy=True, uselist=False)
    credit_transactions = db.relationship('CreditTransaction', backref='sale', lazy=True)

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    receipt_number = db.Column(db.String(50), unique=True)
    file_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Customers (Credit Sales)
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    credit_balance = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='customer', lazy=True)
    credit_transactions = db.relationship('CreditTransaction', backref='customer', lazy=True)

class CreditTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    amount = db.Column(db.Float)
    type = db.Column(db.Enum("credit", "payment", name="credit_types"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Suppliers & Purchases
class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact_person = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='supplier', lazy=True)
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_cost = db.Column(db.Float)
    status = db.Column(db.Enum("pending", "received", "cancelled", name="order_status"))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    items = db.relationship('PurchaseItem', backref='purchase_order', lazy=True, cascade='all, delete-orphan')

class PurchaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    cost_price = db.Column(db.Float)
    subtotal = db.Column(db.Float)

# System Settings
class BusinessSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(120))
    logo_path = db.Column(db.String(255))
    tax_rate = db.Column(db.Float, default=5.0)
    currency = db.Column(db.String(10), default="GHS")
    address = db.Column(db.String(255))
    contact = db.Column(db.String(50))
    contact_email = db.Column(db.String(120))
    website = db.Column(db.String(255))
    opening_time = db.Column(db.String(10), default="08:00")
    closing_time = db.Column(db.String(10), default="18:00")
    timezone = db.Column(db.String(50), default="GMT+0")
    date_format = db.Column(db.String(20), default="DD/MM/YYYY")
    decimal_places = db.Column(db.Integer, default=2)
    # Notification settings
    low_stock_alerts = db.Column(db.Boolean, default=True)
    daily_sales_reports = db.Column(db.Boolean, default=False)
    system_maintenance_alerts = db.Column(db.Boolean, default=True)
    # Security settings
    session_timeout = db.Column(db.Integer, default=30)  # minutes
    min_password_length = db.Column(db.Integer, default=6)
    require_uppercase = db.Column(db.Boolean, default=False)
    require_lowercase = db.Column(db.Boolean, default=False)
    require_numbers = db.Column(db.Boolean, default=False)
    require_special_chars = db.Column(db.Boolean, default=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    activity_logging = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BackupLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(255))
    backup_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    created_by_user = db.relationship('User', backref='backups', lazy=True)
