from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Supplier, PurchaseOrder, PurchaseItem, Product, UserActivityLog
from datetime import datetime
from functools import wraps

suppliers_bp = Blueprint('suppliers', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@suppliers_bp.route('/suppliers')
@login_required
@admin_required
def suppliers():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Supplier.query
    
    if search:
        query = query.filter(
            db.or_(
                Supplier.name.ilike(f'%{search}%'),
                Supplier.contact_person.ilike(f'%{search}%'),
                Supplier.phone.ilike(f'%{search}%')
            )
        )
    
    suppliers = query.order_by(Supplier.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('suppliers/suppliers.html', suppliers=suppliers)

@suppliers_bp.route('/suppliers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_supplier():
    if request.method == 'POST':
        name = request.form.get('name')
        contact_person = request.form.get('contact_person')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        
        supplier = Supplier(
            name=name,
            contact_person=contact_person,
            phone=phone,
            email=email,
            address=address
        )
        db.session.add(supplier)
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Created supplier: {name}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Supplier created successfully!', 'success')
        return redirect(url_for('suppliers.suppliers'))
    
    return render_template('suppliers/create_supplier.html')

@suppliers_bp.route('/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    if request.method == 'POST':
        supplier.name = request.form.get('name')
        supplier.contact_person = request.form.get('contact_person')
        supplier.phone = request.form.get('phone')
        supplier.email = request.form.get('email')
        supplier.address = request.form.get('address')
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Updated supplier: {supplier.name}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Supplier updated successfully!', 'success')
        return redirect(url_for('suppliers.suppliers'))
    
    return render_template('suppliers/edit_supplier.html', supplier=supplier)

@suppliers_bp.route('/suppliers/<int:supplier_id>')
@login_required
@admin_required
def supplier_detail(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Get supplier's products
    products = Product.query.filter_by(supplier_id=supplier_id).all()
    
    # Get purchase orders
    purchase_orders = PurchaseOrder.query.filter_by(supplier_id=supplier_id).order_by(PurchaseOrder.order_date.desc()).all()
    
    return render_template('suppliers/supplier_detail.html', 
                         supplier=supplier, 
                         products=products, 
                         purchase_orders=purchase_orders)

@suppliers_bp.route('/purchase-orders')
@login_required
@admin_required
def purchase_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = PurchaseOrder.query
    
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    
    purchase_orders = query.order_by(PurchaseOrder.order_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('suppliers/purchase_orders.html', purchase_orders=purchase_orders)

@suppliers_bp.route('/purchase-orders/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_purchase_order():
    if request.method == 'POST':
        supplier_id = int(request.form.get('supplier_id'))
        items_data = request.form.getlist('items[]')
        
        if not items_data:
            flash('Please add at least one item', 'error')
        else:
            # Create purchase order
            purchase_order = PurchaseOrder(
                supplier_id=supplier_id,
                created_by=current_user.id,
                status='pending'
            )
            db.session.add(purchase_order)
            db.session.flush()  # Get order ID
            
            total_cost = 0
            
            # Process items
            for i in range(0, len(items_data), 3):
                if i + 2 < len(items_data):
                    product_id = int(items_data[i])
                    quantity = int(items_data[i + 1])
                    cost_price = float(items_data[i + 2])
                    
                    if quantity > 0 and cost_price > 0:
                        purchase_item = PurchaseItem(
                            purchase_order_id=purchase_order.id,
                            product_id=product_id,
                            quantity=quantity,
                            cost_price=cost_price,
                            subtotal=quantity * cost_price
                        )
                        db.session.add(purchase_item)
                        total_cost += purchase_item.subtotal
            
            purchase_order.total_cost = total_cost
            
            # Log activity
            activity = UserActivityLog(
                user_id=current_user.id,
                action=f"Created purchase order #{purchase_order.id} for {total_cost}"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Purchase order created successfully!', 'success')
            return redirect(url_for('suppliers.purchase_orders'))
    
    suppliers = Supplier.query.all()
    products = Product.query.all()
    return render_template('suppliers/create_purchase_order.html', suppliers=suppliers, products=products)

@suppliers_bp.route('/purchase-orders/<int:order_id>')
@login_required
@admin_required
def purchase_order_detail(order_id):
    purchase_order = PurchaseOrder.query.get_or_404(order_id)
    return render_template('suppliers/purchase_order_detail.html', purchase_order=purchase_order)

@suppliers_bp.route('/purchase-orders/<int:order_id>/receive')
@login_required
@admin_required
def receive_purchase_order(order_id):
    purchase_order = PurchaseOrder.query.get_or_404(order_id)
    
    if purchase_order.status != 'pending':
        flash('Order cannot be received', 'error')
    else:
        # Update order status
        purchase_order.status = 'received'
        
        # Update product stock and cost prices
        for item in purchase_order.items:
            product = Product.query.get(item.product_id)
            product.stock_quantity += item.quantity
            product.cost_price = item.cost_price
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Received purchase order #{purchase_order.id}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Purchase order received successfully!', 'success')
    
    return redirect(url_for('suppliers.purchase_order_detail', order_id=order_id))

@suppliers_bp.route('/purchase-orders/<int:order_id>/cancel')
@login_required
@admin_required
def cancel_purchase_order(order_id):
    purchase_order = PurchaseOrder.query.get_or_404(order_id)
    
    if purchase_order.status != 'pending':
        flash('Order cannot be cancelled', 'error')
    else:
        purchase_order.status = 'cancelled'
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Cancelled purchase order #{purchase_order.id}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Purchase order cancelled successfully!', 'success')
    
    return redirect(url_for('suppliers.purchase_order_detail', order_id=order_id))

@suppliers_bp.route('/api/suppliers/search')
@login_required
def search_suppliers():
    query = request.args.get('q', '').lower()
    suppliers = Supplier.query.filter(
        db.or_(
            Supplier.name.ilike(f'%{query}%'),
            Supplier.contact_person.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'contact_person': s.contact_person,
        'phone': s.phone
    } for s in suppliers])
