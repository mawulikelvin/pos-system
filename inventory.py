from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Product, Supplier, StockAdjustment, UserActivityLog
from datetime import datetime
from functools import wraps

inventory_bp = Blueprint('inventory', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@inventory_bp.route('/products')
@login_required
def products():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = Product.query
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.sku.ilike(f'%{search}%'),
                Product.barcode.ilike(f'%{search}%')
            )
        )
    
    if category:
        query = query.filter(Product.category == category)
    
    products = query.order_by(Product.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('inventory/products.html', products=products, categories=categories)

@inventory_bp.route('/products/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_product():
    if request.method == 'POST':
        name = request.form.get('name')
        sku = request.form.get('sku')
        barcode = request.form.get('barcode')
        category = request.form.get('category')
        supplier_id = request.form.get('supplier_id') or None
        price = float(request.form.get('price', 0))
        cost_price = float(request.form.get('cost_price', 0)) or None
        stock_quantity = int(request.form.get('stock_quantity', 0))
        low_stock_threshold = int(request.form.get('low_stock_threshold', 5))
        
        if Product.query.filter_by(sku=sku).first():
            flash('SKU already exists', 'error')
        elif barcode and Product.query.filter_by(barcode=barcode).first():
            flash('Barcode already exists', 'error')
        else:
            product = Product(
                name=name,
                sku=sku,
                barcode=barcode,
                category=category,
                supplier_id=supplier_id,
                price=price,
                cost_price=cost_price,
                stock_quantity=stock_quantity,
                low_stock_threshold=low_stock_threshold
            )
            db.session.add(product)
            
            # Log activity
            activity = UserActivityLog(
                user_id=current_user.id,
                action=f"Created product: {name} (SKU: {sku})"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Product created successfully!', 'success')
            return redirect(url_for('inventory.products'))
    
    suppliers = Supplier.query.all()
    return render_template('inventory/create_product.html', suppliers=suppliers)

@inventory_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.form.get('name')
            product.sku = request.form.get('sku')
            product.barcode = request.form.get('barcode')
            product.category = request.form.get('category')
            product.supplier_id = int(request.form.get('supplier_id')) if request.form.get('supplier_id') else None
            product.price = float(request.form.get('price', 0))
            product.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            product.stock_quantity = int(request.form.get('stock_quantity', 0))
            product.low_stock_threshold = int(request.form.get('low_stock_threshold', 5))
            
            # Log activity
            activity = UserActivityLog(
                user_id=current_user.id,
                action=f"Updated product: {product.name} (SKU: {product.sku})"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('inventory.products'))
            
        except (ValueError, TypeError) as e:
            db.session.rollback()
            flash(f'Error updating product: Invalid input data. Please check your values.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'error')
    
    suppliers = Supplier.query.all()
    return render_template('inventory/edit_product.html', product=product, suppliers=suppliers)

@inventory_bp.route('/products/<int:product_id>/delete')
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if product has sales
    if product.sale_items:
        flash('Cannot delete product with sales history', 'error')
    else:
        db.session.delete(product)
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Deleted product: {product.name} (SKU: {product.sku})"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Product deleted successfully!', 'success')
    
    return redirect(url_for('inventory.products'))

@inventory_bp.route('/stock-adjustments')
@login_required
@admin_required
def stock_adjustments():
    page = request.args.get('page', 1, type=int)
    adjustments = StockAdjustment.query.order_by(StockAdjustment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('inventory/stock_adjustments.html', adjustments=adjustments)

@inventory_bp.route('/stock-adjustments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_stock_adjustment():
    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        adjustment_type = request.form.get('adjustment_type')
        quantity = int(request.form.get('quantity'))
        note = request.form.get('note')
        
        product = Product.query.get_or_404(product_id)
        
        # Create adjustment record
        adjustment = StockAdjustment(
            product_id=product_id,
            adjustment_type=adjustment_type,
            quantity=quantity,
            note=note,
            created_by=current_user.id
        )
        db.session.add(adjustment)
        
        # Update product stock
        if adjustment_type == 'damage':
            product.stock_quantity -= quantity
        elif adjustment_type == 'return':
            product.stock_quantity += quantity
        elif adjustment_type == 'manual':
            # For manual adjustment, we need to know if it's adding or subtracting
            # Let's assume positive quantity means adding, negative means subtracting
            if quantity >= 0:
                product.stock_quantity += quantity
            else:
                # quantity is negative, so this will subtract
                product.stock_quantity += quantity
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Stock adjustment for {product.name}: {adjustment_type} {quantity} units"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Stock adjustment created successfully!', 'success')
        return redirect(url_for('inventory.stock_adjustments'))
    
    products = Product.query.all()
    return render_template('inventory/create_stock_adjustment.html', products=products)

@inventory_bp.route('/low-stock')
@login_required
def low_stock():
    # Fix any negative stock issues first
    products_with_negative_stock = Product.query.filter(Product.stock_quantity < 0).all()
    for product in products_with_negative_stock:
        product.stock_quantity = 0
        db.session.add(product)
    
    if products_with_negative_stock:
        db.session.commit()
        flash(f'Fixed {len(products_with_negative_stock)} products with negative stock', 'warning')
    
    products = Product.query.filter(
        Product.stock_quantity <= Product.low_stock_threshold
    ).order_by(Product.stock_quantity).all()
    return render_template('inventory/low_stock.html', products=products)

@inventory_bp.route('/suppliers')
@login_required
@admin_required
def suppliers():
    page = request.args.get('page', 1, type=int)
    suppliers = Supplier.query.order_by(Supplier.name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('inventory/suppliers.html', suppliers=suppliers)

@inventory_bp.route('/suppliers/create', methods=['GET', 'POST'])
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
        return redirect(url_for('inventory.suppliers'))
    
    return render_template('inventory/create_supplier.html')

@inventory_bp.route('/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
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
        return redirect(url_for('inventory.suppliers'))
    
    return render_template('inventory/edit_supplier.html', supplier=supplier)

@inventory_bp.route('/api/products/categories')
@login_required
def get_categories():
    categories = db.session.query(Product.category).distinct().all()
    return jsonify([cat[0] for cat in categories if cat[0]])
