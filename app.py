from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load configuration based on environment
from config import get_config
config_class = get_config()
app.config.from_object(config_class)

# Import and initialize extensions
from extensions import db, login_manager, migrate, mail
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
mail.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Import blueprints
from auth import auth_bp
from admin import admin_bp
from sales import sales_bp
from inventory import inventory_bp
from customers import customers_bp
from suppliers import suppliers_bp
from reports import reports_bp
from settings import settings_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(sales_bp, url_prefix='/sales')
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(customers_bp, url_prefix='/customers')
app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(settings_bp, url_prefix='/settings')

# Import models after db initialization
from models import User, Product, Sale, Customer, Supplier, BusinessSettings

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_business_settings():
    """Make business settings available globally in all templates"""
    try:
        business_settings = BusinessSettings.query.first()
        return dict(business_settings=business_settings)
    except:
        return dict(business_settings=None)

@app.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('sales.pos'))

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow()})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin user if none exists
        if not User.query.filter_by(role='admin').first():
            from werkzeug.security import generate_password_hash
            admin_user = User(
                username='admin',
                email='admin@pos.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin_user)
            
            # Create default business settings
            if not BusinessSettings.query.first():
                business_settings = BusinessSettings(
                    business_name='My POS System',
                    tax_rate=0.0,
                    currency='GHS',
                    address='123 Business Street',
                    contact='+233 20 123 4567'
                )
                db.session.add(business_settings)
            
            db.session.commit()
            print("Default admin user created: username='admin', password='admin123'")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
