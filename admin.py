from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Product, Sale, Customer, Supplier, UserActivityLog
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get dashboard statistics
    total_users = User.query.count()
    total_products = Product.query.count()
    total_sales = Sale.query.filter_by(status='completed').count()
    total_customers = Customer.query.count()
    
    # Recent sales (increased limit for better scrolling experience)
    recent_sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).limit(15).all()
    
    # Low stock products
    low_stock_products = Product.query.filter(
        Product.stock_quantity <= Product.low_stock_threshold
    ).limit(5).all()
    
    # Recent user activities
    recent_activities = UserActivityLog.query.order_by(UserActivityLog.timestamp.desc()).limit(20).all()
    
    # Sales chart data (last 7 days)
    sales_data = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        daily_sales = Sale.query.filter(
            Sale.created_at >= date.replace(hour=0, minute=0, second=0),
            Sale.created_at < date.replace(hour=23, minute=59, second=59),
            Sale.status == 'completed'
        ).count()
        sales_data.append({'date': date.strftime('%m/%d'), 'sales': daily_sales})
    
    sales_data.reverse()
    
    # Ensure we have at least some data for the chart
    if not sales_data or all(item['sales'] == 0 for item in sales_data):
        # If no sales data, show sample data for demonstration
        sample_dates = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        sales_data = [{'date': date, 'sales': 0} for date in sample_dates]
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_products=total_products,
                         total_sales=total_sales,
                         total_customers=total_customers,
                         recent_sales=recent_sales,
                         low_stock_products=low_stock_products,
                         recent_activities=recent_activities,
                         sales_data=sales_data)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        
        # Validation
        if not all([username, email, password, confirm_password, role]):
            flash('All fields are required', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
        else:
            user = User(
                username=username,
                email=email,
                role=role
            )
            user.set_password(password)
            db.session.add(user)
            
            # Log activity
            activity = UserActivityLog(
                user_id=current_user.id,
                action=f"Created user: {username}"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('User created successfully!', 'success')
            return redirect(url_for('admin.users'))
    
    return render_template('admin/create_user.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        
        if request.form.get('password'):
            user.set_password(request.form.get('password'))
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Updated user: {user.username}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/users/<int:user_id>/deactivate')
@login_required
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account', 'error')
    else:
        user.role = 'staff'  # Change role instead of deleting
        db.session.commit()
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Deactivated user: {user.username}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('User deactivated successfully!', 'success')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/activate')
@login_required
@admin_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot modify your own account status', 'error')
    else:
        user.role = 'cashier'  # Reactivate as cashier
        db.session.commit()
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Activated user: {user.username}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('User activated successfully!', 'success')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/clear-activities', methods=['POST'])
@login_required
@admin_required
def clear_activities():
    try:
        # Delete all activity logs
        deleted_count = UserActivityLog.query.delete()
        db.session.commit()
        
        # Log this action (though it will be the only activity now)
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Cleared all activity logs ({deleted_count} activities removed)"
        )
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {deleted_count} activities',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error clearing activities: {str(e)}'
        }), 500

@admin_bp.route('/activity-logs')
@login_required
@admin_required
def activity_logs():
    page = request.args.get('page', 1, type=int)
    activities = UserActivityLog.query.order_by(UserActivityLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template('admin/activity_logs.html', activities=activities)

@admin_bp.route('/system-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def system_settings():
    from models import BusinessSettings
    
    settings = BusinessSettings.query.first()
    if not settings:
        settings = BusinessSettings()
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        settings.business_name = request.form.get('business_name')
        settings.tax_rate = float(request.form.get('tax_rate', 0))
        settings.currency = request.form.get('currency')
        settings.address = request.form.get('address')
        settings.contact = request.form.get('contact')
        
        db.session.commit()
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action="Updated system settings"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin.system_settings'))
    
    return render_template('admin/system_settings.html', settings=settings)
