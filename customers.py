from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Customer, Sale, CreditTransaction, UserActivityLog
from datetime import datetime
from functools import wraps

customers_bp = Blueprint('customers', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@customers_bp.route('/customers')
@login_required
def customers():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Customer.query
    
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%')
            )
        )
    
    customers = query.order_by(Customer.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate statistics
    total_customers = customers.total
    total_credit_balance = sum(c.credit_balance for c in customers.items)
    total_sales_count = sum(len(c.sales) for c in customers.items)
    
    return render_template('customers/customers.html', 
                         customers=customers,
                         total_customers=total_customers,
                         total_credit_balance=total_credit_balance,
                         total_sales_count=total_sales_count)

@customers_bp.route('/customers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        customer = Customer(
            name=name,
            phone=phone,
            email=email
        )
        db.session.add(customer)
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Created customer: {name}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Customer created successfully!', 'success')
        return redirect(url_for('customers.customers'))
    
    return render_template('customers/create_customer.html')

@customers_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.phone = request.form.get('phone')
        customer.email = request.form.get('email')
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Updated customer: {customer.name}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers.customers'))
    
    return render_template('customers/edit_customer.html', customer=customer)

@customers_bp.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Get customer's sales history
    sales = Sale.query.filter_by(customer_id=customer_id).order_by(Sale.created_at.desc()).all()
    
    # Get credit transactions
    credit_transactions = CreditTransaction.query.filter_by(customer_id=customer_id).order_by(CreditTransaction.created_at.desc()).all()
    
    return render_template('customers/customer_detail.html', 
                         customer=customer, 
                         sales=sales, 
                         credit_transactions=credit_transactions)

@customers_bp.route('/customers/<int:customer_id>/add-credit', methods=['GET', 'POST'])
@login_required
@admin_required
def add_credit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        note = request.form.get('note', 'Credit added')
        
        # Create credit transaction
        credit_transaction = CreditTransaction(
            customer_id=customer_id,
            type='credit',
            amount=amount
        )
        db.session.add(credit_transaction)
        
        # Update customer credit balance
        customer.credit_balance += amount
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Added credit for {customer.name}: {amount}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'Credit of {amount} added successfully!', 'success')
        return redirect(url_for('customers.customer_detail', customer_id=customer_id))
    
    return render_template('customers/add_credit.html', customer=customer)

@customers_bp.route('/customers/<int:customer_id>/record-payment', methods=['GET', 'POST'])
@login_required
@admin_required
def record_payment(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        note = request.form.get('note', 'Payment received')
        
        if amount > customer.credit_balance:
            flash('Payment amount cannot exceed credit balance', 'error')
        else:
            # Create payment transaction
            payment_transaction = CreditTransaction(
                customer_id=customer_id,
                type='payment',
                amount=amount
            )
            db.session.add(payment_transaction)
            
            # Update customer credit balance
            customer.credit_balance -= amount
            
            # Log activity
            activity = UserActivityLog(
                user_id=current_user.id,
                action=f"Recorded payment for {customer.name}: {amount}"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash(f'Payment of {amount} recorded successfully!', 'success')
            return redirect(url_for('customers.customer_detail', customer_id=customer_id))
    
    return render_template('customers/record_payment.html', customer=customer)

@customers_bp.route('/credit-sales')
@login_required
def credit_sales():
    page = request.args.get('page', 1, type=int)
    
    # Get sales with customers (credit sales)
    sales = db.session.query(Sale, Customer).join(Customer).filter(
        Sale.customer_id.isnot(None)
    ).order_by(Sale.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('customers/credit_sales.html', sales=sales)

@customers_bp.route('/api/customers/search')
@login_required
def search_customers():
    query = request.args.get('q', '').lower()
    customers = Customer.query.filter(
        db.or_(
            Customer.name.ilike(f'%{query}%'),
            Customer.phone.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'credit_balance': c.credit_balance
    } for c in customers])
