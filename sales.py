from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from extensions import db
from models import Product, Sale, SaleItem, Customer, Receipt, UserActivityLog, BusinessSettings
from datetime import datetime
import uuid

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/pos')
@login_required
def pos():
    # Get products for search
    products = Product.query.filter(Product.stock_quantity > 0).all()
    return render_template('sales/pos.html', products=products)

@sales_bp.route('/api/products/search')
@login_required
def search_products():
    query = request.args.get('q', '').lower()
    products = Product.query.filter(
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.sku.ilike(f'%{query}%'),
            Product.barcode.ilike(f'%{query}%')
        ),
        Product.stock_quantity > 0
    ).limit(10).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'price': p.price,
        'stock': p.stock_quantity
    } for p in products])

@sales_bp.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    
    product = Product.query.get_or_404(product_id)
    
    if product.stock_quantity < quantity:
        return jsonify({'error': 'Insufficient stock'}), 400
    
    # Initialize cart in session if not exists
    if 'cart' not in session:
        session['cart'] = []
    
    # Check if product already in cart
    cart_item = next((item for item in session['cart'] if item['product_id'] == product_id), None)
    
    if cart_item:
        cart_item['quantity'] += quantity
    else:
        session['cart'].append({
            'product_id': product_id,
            'name': product.name,
            'price': product.price,
            'quantity': quantity,
            'total': product.price * quantity
        })
    
    session.modified = True
    return jsonify({'message': 'Added to cart', 'cart_count': len(session['cart'])})

@sales_bp.route('/api/cart/update', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 0))
    
    if 'cart' not in session:
        return jsonify({'error': 'Cart is empty'}), 400
    
    cart_item = next((item for item in session['cart'] if item['product_id'] == product_id), None)
    
    if cart_item:
        if quantity <= 0:
            session['cart'].remove(cart_item)
        else:
            cart_item['quantity'] = quantity
            cart_item['total'] = cart_item['price'] * quantity
        session.modified = True
    
    return jsonify({'message': 'Cart updated'})

@sales_bp.route('/api/cart/clear')
@login_required
def clear_cart():
    session.pop('cart', None)
    return jsonify({'message': 'Cart cleared'})

@sales_bp.route('/api/cart')
@login_required
def get_cart():
    cart = session.get('cart', [])
    total = sum(item['total'] for item in cart)
    return jsonify({'cart': cart, 'total': total})

@sales_bp.route('/api/cart/sync', methods=['POST'])
@login_required
def sync_cart():
    data = request.get_json()
    cart_data = data.get('cart', [])
    
    # Update session cart
    session['cart'] = cart_data
    session.modified = True
    
    return jsonify({'message': 'Cart synced successfully'})

@sales_bp.route('/api/held-sales')
@login_required
def get_held_sales():
    # Get all held sales from session
    held_sales = {}
    for key in session.keys():
        if key.startswith('hold_'):
            hold_id = key.replace('hold_', '')
            held_sales[hold_id] = session[key]
    
    return jsonify({'held_sales': held_sales})

@sales_bp.route('/api/held-sales/clear', methods=['POST'])
@login_required
def clear_held_sales():
    # Clear all held sales from session
    cleared_count = 0
    for key in list(session.keys()):
        if key.startswith('hold_'):
            session.pop(key)
            cleared_count += 1
    
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': f'Cleared {cleared_count} held sales',
        'cleared_count': cleared_count
    })

@sales_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        cart = session.get('cart', [])
        if not cart:
            flash('Cart is empty', 'error')
            return redirect(url_for('sales.pos'))
        
        payment_method = request.form.get('payment_method')
        if not payment_method:
            flash('Payment method is required', 'error')
            return redirect(url_for('sales.checkout'))
        
        customer_id = request.form.get('customer_id') or None
        
        # Handle discount amount properly - convert empty string to 0
        discount_str = request.form.get('discount_amount', '0')
        try:
            discount_amount = float(discount_str) if discount_str.strip() else 0.0
            if discount_amount < 0:
                discount_amount = 0.0
        except (ValueError, TypeError):
            discount_amount = 0.0
        
        # Validate discount doesn't exceed subtotal
        subtotal = sum(item['total'] for item in cart)
        if discount_amount > subtotal:
            discount_amount = subtotal
            flash('Discount amount adjusted to match subtotal', 'info')
        
        # Validate stock availability before processing
        for item in cart:
            product = Product.query.get(item['product_id'])
            if not product:
                flash(f'Product not found: {item["name"]}', 'error')
                return redirect(url_for('sales.checkout'))
            
            if product.stock_quantity < item['quantity']:
                flash(f'Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {item["quantity"]}', 'error')
                return redirect(url_for('sales.checkout'))
        
        # Calculate totals
        subtotal = sum(item['total'] for item in cart)
        total_amount = subtotal - discount_amount
        
        try:
            # Create sale
            sale = Sale(
                cashier_id=current_user.id,
                customer_id=customer_id,
                total_amount=total_amount,
                discount_amount=discount_amount,
                payment_method=payment_method,
                status='completed'
            )
            db.session.add(sale)
            db.session.flush()  # Get sale ID
            
            # Create sale items
            for item in cart:
                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    unit_price=item['price'],
                    total_price=item['total']
                )
                db.session.add(sale_item)
            
            # Create receipt
            receipt = Receipt(
                sale_id=sale.id,
                receipt_number=f"R{sale.id:06d}"
            )
            db.session.add(receipt)
            
            # Log activity
            activity = UserActivityLog(
                user_id=current_user.id,
                action=f"Processed sale #{sale.id} for {total_amount}"
            )
            db.session.add(activity)
            
            # Commit the sale first
            db.session.commit()
            
            # Now update product stock after successful sale
            for item in cart:
                product = Product.query.get(item['product_id'])
                product.stock_quantity -= item['quantity']
            
            # Commit stock updates
            db.session.commit()
            
            # Clear cart
            session.pop('cart', None)
            
            flash(f'Sale completed successfully! Receipt: {receipt.receipt_number}', 'success')
            return redirect(url_for('sales.receipt', sale_id=sale.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing sale: {str(e)}', 'error')
            return redirect(url_for('sales.checkout'))
    
    cart = session.get('cart', [])
    customers = Customer.query.all()
    return render_template('sales/checkout.html', cart=cart, customers=customers)

@sales_bp.route('/receipt/<int:sale_id>')
@login_required
def receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    business_settings = BusinessSettings.query.first()
    return render_template('sales/receipt.html', sale=sale, business_settings=business_settings)

@sales_bp.route('/receipt/<int:sale_id>/download')
@login_required
def download_receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    business_settings = BusinessSettings.query.first()
    
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from io import BytesIO
    
    # Create PDF buffer for 80mm thermal receipt (3.15 inches wide)
    from reportlab.lib.pagesizes import A4
    thermal_width = 3.15*inch  # 80mm
    thermal_height = 11*inch   # Long receipt format
    thermal_pagesize = (thermal_width, thermal_height)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=thermal_pagesize, leftMargin=0.1*inch, rightMargin=0.1*inch, topMargin=0.2*inch, bottomMargin=0.2*inch)
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        spaceAfter=6,
        alignment=1  # Center alignment for thermal receipt
    )
    
    # Title
    business_name = "SALE RECEIPT"
    if business_settings and business_settings.business_name:
        business_name = f"{business_settings.business_name} - SALE RECEIPT"
    
    elements.append(Paragraph(business_name, title_style))
    
    # Add business contact information
    if business_settings:
        contact_style = ParagraphStyle(
            'ContactInfo',
            parent=styles['Normal'],
            fontSize=8,
            spaceAfter=3,
            alignment=1  # Center alignment
        )
        
        if business_settings.contact_email:
            elements.append(Paragraph(f"Email: {business_settings.contact_email}", contact_style))
        
        if business_settings.contact:
            elements.append(Paragraph(f"Phone: {business_settings.contact}", contact_style))
    
    elements.append(Spacer(1, 10))
    
    # Sale information
    sale_info = [
        ['Sale ID:', f"#{sale.id}"],
        ['Date:', sale.created_at.strftime('%d/%m/%Y %H:%M')],
        ['Cashier:', sale.cashier.username],
        ['Payment Method:', sale.payment_method.title()],
        ['Status:', sale.status.title()]
    ]
    
    if sale.customer:
        sale_info.extend([
            ['Customer:', sale.customer.name],
            ['Phone:', sale.customer.phone or 'N/A'],
            ['Email:', sale.customer.email or 'N/A']
        ])
    
    sale_table = Table(sale_info, colWidths=[0.8*inch, 2.2*inch])
    sale_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(sale_table)
    elements.append(Spacer(1, 20))
    
    # Items table
    elements.append(Paragraph("Items Purchased", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    # Table header - simplified for thermal receipt
    items_data = [['Product', 'Qty', 'Price', 'Total']]
    
    # Add items
    for item in sale.items:
        items_data.append([
            item.product.name[:20],  # Truncate long product names
            str(item.quantity),
            f"GH₵{item.unit_price:.2f}",
            f"GH₵{item.total_price:.2f}"
        ])
    
    # Add totals row
    subtotal = sale.total_amount + sale.discount_amount
    items_data.append(['', '', 'Subtotal:', f"GH₵{subtotal:.2f}"])
    
    if sale.discount_amount > 0:
        items_data.append(['', '', 'Discount:', f"-GH₵{sale.discount_amount:.2f}"])
    
    items_data.append(['', '', 'Total:', f"GH₵{sale.total_amount:.2f}"])
    
    items_table = Table(items_data, colWidths=[1.4*inch, 0.4*inch, 0.4*inch, 0.7*inch])
    items_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    
    # Footer
    elements.append(Paragraph("Thank you for your purchase!", styles['Normal']))
    elements.append(Paragraph(f"Receipt Number: {sale.receipt.receipt_number}", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    from flask import send_file
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{sale.receipt.receipt_number}.pdf",
        mimetype='application/pdf'
    )

@sales_bp.route('/receipt/<int:sale_id>/email', methods=['GET', 'POST'])
@login_required
def email_receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    
    if request.method == 'GET':
        # Redirect to view_sale page if accessed via GET
        return redirect(url_for('sales.view_sale', sale_id=sale_id))
    
    # Get recipient email from form
    recipient_email = request.form.get('recipient_email')
    custom_message = request.form.get('email_message', '')
    
    if not recipient_email:
        flash('Please provide a recipient email address', 'error')
        return redirect(url_for('sales.view_sale', sale_id=sale_id))
    
    try:
        # Generate PDF receipt using the same thermal format as download_receipt
        business_settings = BusinessSettings.query.first()
        
        # Create PDF buffer for 80mm thermal receipt (3.15 inches wide)
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO
        
        thermal_width = 3.15*inch  # 80mm
        thermal_height = 11*inch   # Long receipt format
        thermal_pagesize = (thermal_width, thermal_height)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=thermal_pagesize, leftMargin=0.1*inch, rightMargin=0.1*inch, topMargin=0.2*inch, bottomMargin=0.2*inch)
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=12,
            spaceAfter=6,
            alignment=1  # Center alignment for thermal receipt
        )
        
        # Title
        business_name = "SALE RECEIPT"
        if business_settings and business_settings.business_name:
            business_name = f"{business_settings.business_name} - SALE RECEIPT"
        
        elements.append(Paragraph(business_name, title_style))
        
        # Add business contact information
        if business_settings:
            contact_style = ParagraphStyle(
                'ContactInfo',
                parent=styles['Normal'],
                fontSize=8,
                spaceAfter=3,
                alignment=1  # Center alignment
            )
            
            if business_settings.contact_email:
                elements.append(Paragraph(f"Email: {business_settings.contact_email}", contact_style))
            
            if business_settings.contact:
                elements.append(Paragraph(f"Phone: {business_settings.contact}", contact_style))
        
        elements.append(Spacer(1, 8))
        
        # Sale information
        sale_info = [
            ['Sale ID:', f"#{sale.id}"],
            ['Date:', sale.created_at.strftime('%d/%m/%Y %H:%M')],
            ['Cashier:', sale.cashier.username],
            ['Payment Method:', sale.payment_method.title()],
            ['Status:', sale.status.title()]
        ]
        
        if sale.customer:
            sale_info.extend([
                ['Customer:', sale.customer.name],
                ['Phone:', sale.customer.phone or 'N/A'],
                ['Email:', sale.customer.email or 'N/A']
            ])
        
        sale_table = Table(sale_info, colWidths=[0.8*inch, 2.2*inch])
        sale_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(sale_table)
        elements.append(Spacer(1, 10))
        
        # Items table
        items_heading_style = ParagraphStyle(
            'ItemsHeading',
            parent=styles['Heading2'],
            fontSize=10,
            spaceAfter=4,
            alignment=1
        )
        elements.append(Paragraph("Items Purchased", items_heading_style))
        elements.append(Spacer(1, 6))
        
        items_data = [['Product', 'Qty', 'Price', 'Total']]
        
        for item in sale.items:
            items_data.append([
                item.product.name[:20],  # Truncate long product names
                str(item.quantity),
                f"GH₵{item.unit_price:.2f}",
                f"GH₵{item.total_price:.2f}"
            ])
        
        subtotal = sale.total_amount + sale.discount_amount
        items_data.append(['', '', 'Subtotal:', f"GH₵{subtotal:.2f}"])
        
        if sale.discount_amount > 0:
            items_data.append(['', '', 'Discount:', f"-GH₵{sale.discount_amount:.2f}"])
        
        items_data.append(['', '', 'Total:', f"GH₵{sale.total_amount:.2f}"])
        
        items_table = Table(items_data, colWidths=[1.4*inch, 0.4*inch, 0.4*inch, 0.7*inch])
        items_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Thank you for your purchase!", styles['Normal']))
        elements.append(Paragraph(f"Receipt Number: {sale.receipt.receipt_number}", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        
        # Send email using utility function with custom recipient and message
        from email_utils import send_receipt_email_to_address
        success, message = send_receipt_email_to_address(sale, buffer, recipient_email, custom_message)
        
        if success:
            flash(f'Receipt successfully sent to {recipient_email}', 'success')
        else:
            flash(f'Failed to send receipt: {message}', 'error')
        
    except Exception as e:
        flash(f'Error generating receipt: {str(e)}', 'error')
    
    return redirect(url_for('sales.view_sale', sale_id=sale_id))

@sales_bp.route('/new-sale')
@login_required
def new_sale():
    # Clear any existing cart only (don't clear held sales)
    session.pop('cart', None)
    
    flash('Starting new sale', 'info')
    return redirect(url_for('sales.pos'))

@sales_bp.route('/clear-all-held-sales')
@login_required
def clear_all_held_sales():
    # Clear all held sales
    held_sales_count = 0
    for key in list(session.keys()):
        if key.startswith('hold_'):
            session.pop(key)
            held_sales_count += 1
    
    if held_sales_count > 0:
        flash(f'Cleared {held_sales_count} held sales', 'info')
    else:
        flash('No held sales to clear', 'info')
    
    return redirect(url_for('sales.pos'))

@sales_bp.route('/hold-sale')
@login_required
def hold_sale():
    cart = session.get('cart', [])
    if not cart:
        flash('Cart is empty', 'error')
        return redirect(url_for('sales.pos'))
    
    # Generate hold ID
    hold_id = str(uuid.uuid4())[:8]
    
    # Store cart in session with hold ID
    session[f'hold_{hold_id}'] = cart
    session.pop('cart', None)
    
    flash(f'Sale held with ID: {hold_id}', 'info')
    return redirect(url_for('sales.pos'))

@sales_bp.route('/resume-sale/<hold_id>')
@login_required
def resume_sale(hold_id):
    held_cart = session.get(f'hold_{hold_id}')
    if held_cart:
        session['cart'] = held_cart
        session.pop(f'hold_{hold_id}', None)
        flash('Sale resumed', 'info')
    else:
        flash('Held sale not found', 'error')
    
    return redirect(url_for('sales.pos'))

@sales_bp.route('/refund/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def refund_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    
    if request.method == 'POST':
        refund_reason = request.form.get('refund_reason')
        
        # Update sale status
        sale.status = 'refunded'
        
        # Restore product stock
        for item in sale.items:
            product = Product.query.get(item.product_id)
            product.stock_quantity += item.quantity
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Refunded sale #{sale.id}: {refund_reason}"
        )
        db.session.add(activity)
        
        db.session.commit()
        flash('Sale refunded successfully', 'success')
        return redirect(url_for('sales.pos'))
    
    return render_template('sales/refund.html', sale=sale)

@sales_bp.route('/sales-history')
@login_required
def sales_history():
    # Get 10 most recent completed sales for the table
    recent_sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).limit(10).all()
    
    # Calculate overall statistics from all completed sales
    all_completed_sales = Sale.query.filter_by(status='completed').all()
    total_sales = len(all_completed_sales)
    total_revenue = sum(sale.total_amount for sale in all_completed_sales)
    
    # Calculate today's sales
    from datetime import datetime, date
    today = date.today()
    today_sales_count = sum(1 for sale in all_completed_sales if sale.created_at.date() == today)
    
    # Create a mock pagination object for template compatibility
    class MockPagination:
        def __init__(self, items):
            self.items = items
            self.total = len(items)
            self.pages = 1
            self.page = 1
            self.has_prev = False
            self.has_next = False
    
    sales = MockPagination(recent_sales)
    
    return render_template('sales/sales_history.html', 
                         sales=sales,
                         total_sales=total_sales,
                         total_revenue=total_revenue,
                         today_sales_count=today_sales_count)

@sales_bp.route('/all-sales-history')
@login_required
def all_sales_history():
    page = request.args.get('page', 1, type=int)
    sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate statistics
    total_sales = sales.total
    total_revenue = sum(sale.total_amount for sale in sales.items)
    
    # Calculate today's sales
    from datetime import datetime, date
    today = date.today()
    today_sales_count = sum(1 for sale in sales.items if sale.created_at.date() == today)
    
    return render_template('sales/all_sales_history.html', 
                         sales=sales,
                         total_sales=total_sales,
                         total_revenue=total_revenue,
                         today_sales_count=today_sales_count)

@sales_bp.route('/view-sale/<int:sale_id>')
@login_required
def view_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    
    # Calculate sale age
    from datetime import date
    today = date.today()
    sale_date = sale.created_at.date()
    
    if sale_date == today:
        sale_age = "Today"
    elif sale_date == today.replace(day=today.day - 1):
        sale_age = "Yesterday"
    else:
        days_diff = (today - sale_date).days
        sale_age = f"{days_diff} days ago"
    
    return render_template('sales/view_sale.html', sale=sale, sale_age=sale_age)

@sales_bp.route('/api/stock/<int:product_id>')
@login_required
def get_stock(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'product_id': product.id,
        'stock_quantity': product.stock_quantity,
        'low_stock_threshold': product.low_stock_threshold,
        'is_low_stock': product.stock_quantity <= product.low_stock_threshold
    })
