from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, UserActivityLog
from datetime import datetime
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            
            # Log user activity
            activity = UserActivityLog(
                user_id=user.id,
                action=f"User logged in from {request.remote_addr}"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validation
        if not all([username, email, password, confirm_password, full_name]):
            flash('All required fields must be filled', 'error')
            return render_template('auth/signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/signup.html')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/signup.html')
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            role='cashier'  # New signups get cashier role
        )
        new_user.set_password(password)
        
        # Add additional user properties (you may need to extend the User model)
        # For now, we'll store additional info in a note or extend the model later
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Log the signup activity
            activity = UserActivityLog(
                user_id=new_user.id,
                action=f"New user account created: {username}"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Account created successfully! You can now login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating account. Please try again.', 'error')
            print(f"Signup error: {e}")
    
    return render_template('auth/signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Log logout activity
    activity = UserActivityLog(
        user_id=current_user.id,
        action=f"User logged out from {request.remote_addr}"
    )
    db.session.add(activity)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'error')
        elif len(new_password) < 6:
            flash('New password must be at least 6 characters long', 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            
            # Log password change
            activity = UserActivityLog(
                user_id=current_user.id,
                action="Password changed"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('index'))
    
    return render_template('auth/change_password.html')
