#!/bin/bash

# Render Build Script for POS System
echo "Starting build process..."

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p static/uploads
mkdir -p instance

# Initialize database and create tables
python -c "
from app import app, db
from models import *
import os

with app.app_context():
    # Create all tables
    db.create_all()
    print('Database tables created successfully!')
    
    # Create default admin user if not exists
    from werkzeug.security import generate_password_hash
    from models import User
    
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin_user = User(
            username='admin',
            email='admin@pos.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print('Default admin user created: admin/admin123')
    else:
        print('Admin user already exists')
"

echo "Build completed successfully!"
