#!/usr/bin/env python3
"""
POS System Startup Script
Run this script to start the Point of Sale system.
"""

import os
import sys
from app import app
from extensions import db
from models import User, BusinessSettings, Product, Supplier, Customer
from werkzeug.security import generate_password_hash
from config import get_config

def create_default_data():
    """Create default admin user and business settings if they don't exist."""
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create default admin user if none exists
        if not User.query.filter_by(role='admin').first():
            admin_user = User(
                username='admin',
                email='admin@pos.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin_user)
            print("Default admin user created")
            print("  Username: admin")
            print("  Password: admin123")
            print("  IMPORTANT: Change this password after first login!")
        
        # Create default business settings if none exist
        if not BusinessSettings.query.first():
            business_settings = BusinessSettings(
                business_name='My POS System', 
                tax_rate=5.0, 
                currency='GHS', 
                address='123 Business Street, Accra, Ghana', 
                contact='+233 20 123 4567',
                contact_email='info@mypos.com',
                website='https://mypos.com',
                opening_time='08:00',
                closing_time='18:00',
                timezone='GMT+0',
                date_format='DD/MM/YYYY',
                decimal_places=2
            )
            db.session.add(business_settings)
            print("Default business settings created")
        
        # Create some sample products if none exist
        
        if not Product.query.first():
            # Create sample supplier
            supplier = Supplier(
                name='Sample Supplier',
                contact_person='John Doe',
                phone='+233 20 123 4567',
                email='supplier@example.com',
                address='456 Supplier Street, Accra, Ghana'
            )
            db.session.add(supplier)
            db.session.flush()
            
            # Create sample products
            sample_products = [
                {
                    'name': 'Rice (5kg Bag)',
                    'sku': 'RICE001',
                    'barcode': '1234567890123',
                    'category': 'Food & Beverages',
                    'price': 45.00,
                    'cost_price': 35.00,
                    'stock_quantity': 100,
                    'low_stock_threshold': 20,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Cooking Oil (1L)',
                    'sku': 'OIL001',
                    'barcode': '1234567890124',
                    'category': 'Food & Beverages',
                    'price': 12.50,
                    'cost_price': 9.00,
                    'stock_quantity': 80,
                    'low_stock_threshold': 15,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Bread (Large Loaf)',
                    'sku': 'BREAD001',
                    'barcode': '1234567890125',
                    'category': 'Food & Beverages',
                    'price': 8.00,
                    'cost_price': 5.50,
                    'stock_quantity': 50,
                    'low_stock_threshold': 10,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Tomatoes (1kg)',
                    'sku': 'VEG001',
                    'barcode': '1234567890126',
                    'category': 'Fresh Produce',
                    'price': 15.00,
                    'cost_price': 10.00,
                    'stock_quantity': 60,
                    'low_stock_threshold': 12,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Onions (1kg)',
                    'sku': 'VEG002',
                    'barcode': '1234567890127',
                    'category': 'Fresh Produce',
                    'price': 8.50,
                    'cost_price': 6.00,
                    'stock_quantity': 75,
                    'low_stock_threshold': 15,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Chicken (1kg)',
                    'sku': 'MEAT001',
                    'barcode': '1234567890128',
                    'category': 'Meat & Fish',
                    'price': 35.00,
                    'cost_price': 28.00,
                    'stock_quantity': 40,
                    'low_stock_threshold': 8,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Fish (1kg)',
                    'sku': 'MEAT002',
                    'barcode': '1234567890129',
                    'category': 'Meat & Fish',
                    'price': 45.00,
                    'cost_price': 35.00,
                    'stock_quantity': 30,
                    'low_stock_threshold': 6,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Milk (1L)',
                    'sku': 'DAIRY001',
                    'barcode': '1234567890130',
                    'category': 'Dairy',
                    'price': 18.00,
                    'cost_price': 14.00,
                    'stock_quantity': 70,
                    'low_stock_threshold': 12,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Eggs (30 pieces)',
                    'sku': 'DAIRY002',
                    'barcode': '1234567890131',
                    'category': 'Dairy',
                    'price': 25.00,
                    'cost_price': 20.00,
                    'stock_quantity': 45,
                    'low_stock_threshold': 10,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Soap (Bar)',
                    'sku': 'HOME001',
                    'barcode': '1234567890132',
                    'category': 'Home & Personal Care',
                    'price': 5.00,
                    'cost_price': 3.50,
                    'stock_quantity': 120,
                    'low_stock_threshold': 25,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Toothpaste',
                    'sku': 'HOME002',
                    'barcode': '1234567890133',
                    'category': 'Home & Personal Care',
                    'price': 12.00,
                    'cost_price': 8.50,
                    'stock_quantity': 90,
                    'low_stock_threshold': 18,
                    'supplier_id': supplier.id
                },
                {
                    'name': 'Batteries (AA Pack)',
                    'sku': 'ELEC001',
                    'barcode': '1234567890134',
                    'category': 'Electronics',
                    'price': 15.00,
                    'cost_price': 11.00,
                    'stock_quantity': 60,
                    'low_stock_threshold': 12,
                    'supplier_id': supplier.id
                }
            ]
            
            for product_data in sample_products:
                product = Product(**product_data)
                db.session.add(product)
            
            print("Sample supplier and products created")
        
        # Create some sample customers if none exist
        if not Customer.query.first():
            sample_customers = [
                {
                    'name': 'John Doe',
                    'email': 'john.doe@example.com',
                    'phone': '+233 20 123 4567'
                },
                {
                    'name': 'Jane Smith',
                    'email': 'jane.smith@example.com',
                    'phone': '+233 20 234 5678'
                },
                {
                    'name': 'Peter Jones',
                    'email': 'peter.jones@example.com',
                    'phone': '+233 20 345 6789'
                }
            ]
            
            for customer_data in sample_customers:
                customer = Customer(**customer_data)
                db.session.add(customer)
            
            print("Sample customers created")
        
        try:
            db.session.commit()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()

def main():
    """Main function to run the application."""
    print("Starting POS System...")
    
    # Create default data
    create_default_data()
    
    # Get configuration
    app.config.from_object(get_config())
    
    # Run the application
    print("POS System is running!")
    print("  Open your browser and go to: http://localhost:5000")
    print("  Login with: admin / admin123")
    print("  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=app.config.get('DEBUG', False)
        )
    except KeyboardInterrupt:
        print("\nPOS System stopped by user")
    except Exception as e:
        print(f"Error running POS System: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
