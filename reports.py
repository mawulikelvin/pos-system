from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from extensions import db
from models import Sale, SaleItem, Product, User, Customer
from datetime import datetime, timedelta
from functools import wraps
import csv
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

reports_bp = Blueprint('reports', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@reports_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get date range from request
    period = request.args.get('period', '7d')
    
    if period == '7d':
        start_date = datetime.now() - timedelta(days=7)
    elif period == '30d':
        start_date = datetime.now() - timedelta(days=30)
    elif period == '90d':
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime.now() - timedelta(days=7)
    
    # Sales data
    sales = Sale.query.filter(
        Sale.created_at >= start_date,
        Sale.status == 'completed'
    ).all()
    
    total_sales = len(sales)
    total_revenue = sum(sale.total_amount for sale in sales)
    avg_sale = total_revenue / total_sales if total_sales > 0 else 0
    
    # Recent sales for display
    recent_sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).limit(20).all()
    
    # Top products
    product_sales = db.session.query(
        Product.name,
        db.func.sum(SaleItem.quantity).label('total_quantity'),
        db.func.sum(SaleItem.total_price).label('total_revenue')
    ).join(SaleItem).join(Sale).filter(
        Sale.created_at >= start_date,
        Sale.status == 'completed'
    ).group_by(Product.id, Product.name).order_by(
        db.func.sum(SaleItem.total_price).desc()
    ).limit(10).all()
    
    # Sales by day
    daily_sales = []
    current_date = start_date
    while current_date <= datetime.now():
        next_date = current_date + timedelta(days=1)
        daily_count = Sale.query.filter(
            Sale.created_at >= current_date,
            Sale.created_at < next_date,
            Sale.status == 'completed'
        ).count()
        daily_sales.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'sales': daily_count
        })
        current_date = next_date
    
    return render_template('reports/dashboard.html',
                         period=period,
                         total_sales=total_sales,
                         total_revenue=total_revenue,
                         avg_sale=avg_sale,
                         product_sales=product_sales,
                         daily_sales=daily_sales,
                         recent_sales=recent_sales)

@reports_bp.route('/sales-report')
@login_required
@admin_required
def sales_report():
    # Get filters from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    payment_method = request.args.get('payment_method', '')
    
    query = Sale.query.filter(Sale.status == 'completed')
    
    if start_date:
        query = query.filter(Sale.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Sale.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    if payment_method:
        query = query.filter(Sale.payment_method == payment_method)
    
    sales = query.order_by(Sale.created_at.desc()).all()
    
    # Calculate totals
    total_sales = len(sales)
    total_revenue = sum(sale.total_amount for sale in sales)
    total_discounts = sum(sale.discount_amount for sale in sales)
    
    # Payment method breakdown
    payment_breakdown = {}
    for sale in sales:
        method = sale.payment_method
        if method not in payment_breakdown:
            payment_breakdown[method] = {'count': 0, 'amount': 0}
        payment_breakdown[method]['count'] += 1
        payment_breakdown[method]['amount'] += sale.total_amount
    
    return render_template('reports/sales_report.html',
                         sales=sales,
                         total_sales=total_sales,
                         total_revenue=total_revenue,
                         total_discounts=total_discounts,
                         payment_breakdown=payment_breakdown)

@reports_bp.route('/product-report')
@login_required
@admin_required
def product_report():
    # Get product performance data
    products = db.session.query(
        Product.id,
        Product.name,
        Product.sku,
        Product.category,
        Product.stock_quantity,
        db.func.sum(SaleItem.quantity).label('total_sold'),
        db.func.sum(SaleItem.total_price).label('total_revenue')
    ).outerjoin(SaleItem).outerjoin(Sale).filter(
        Sale.status == 'completed'
    ).group_by(Product.id, Product.name, Product.sku, Product.category, Product.stock_quantity).all()
    
    # Calculate profit margins (if cost price is available)
    for product in products:
        if hasattr(product, 'cost_price') and product.cost_price:
            product.profit_margin = ((product.total_revenue or 0) - (product.total_sold or 0) * product.cost_price) / (product.total_revenue or 1) * 100
        else:
            product.profit_margin = 0
    
    return render_template('reports/product_report.html', products=products)

@reports_bp.route('/staff-report')
@login_required
@admin_required
def staff_report():
    # Get staff performance data
    staff_performance = db.session.query(
        User.id,
        User.username,
        User.role,
        db.func.count(Sale.id).label('total_sales'),
        db.func.sum(Sale.total_amount).label('total_revenue'),
        db.func.avg(Sale.total_amount).label('avg_sale')
    ).outerjoin(Sale).filter(
        Sale.status == 'completed'
    ).group_by(User.id, User.username, User.role).all()
    
    return render_template('reports/staff_report.html', staff_performance=staff_performance)

@reports_bp.route('/export/sales-csv')
@login_required
@admin_required
def export_sales_csv():
    # Get sales data
    sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Sale ID', 'Date', 'Cashier', 'Customer', 'Items', 'Subtotal', 'Discount', 'Total', 'Payment Method'])
    
    # Write data
    for sale in sales:
        items_count = len(sale.items)
        writer.writerow([
            sale.id,
            sale.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            sale.cashier.username if sale.cashier else 'N/A',
            sale.customer.name if sale.customer else 'Walk-in',
            items_count,
            sale.total_amount + sale.discount_amount,
            sale.discount_amount,
            sale.total_amount,
            sale.payment_method
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'sales_report_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@reports_bp.route('/export/sales-pdf')
@login_required
@admin_required
def export_sales_pdf():
    # Get sales data
    sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).limit(100).all()
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Title
    styles = getSampleStyleSheet()
    title = Paragraph("Sales Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Table data
    data = [['Sale ID', 'Date', 'Cashier', 'Total', 'Payment Method']]
    for sale in sales:
        data.append([
            str(sale.id),
            sale.created_at.strftime('%Y-%m-%d'),
            sale.cashier.username if sale.cashier else 'N/A',
            f"{sale.total_amount:.2f}",
            sale.payment_method
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'sales_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )

@reports_bp.route('/export/inventory-csv')
@login_required
@admin_required
def export_inventory_csv():
    # Get inventory data
    products = Product.query.all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['SKU', 'Name', 'Category', 'Price', 'Cost Price', 'Stock', 'Low Stock Threshold', 'Supplier'])
    
    # Write data
    for product in products:
        writer.writerow([
            product.sku,
            product.name,
            product.category or 'N/A',
            product.price,
            product.cost_price or 'N/A',
            product.stock_quantity,
            product.low_stock_threshold,
            product.supplier.name if product.supplier else 'N/A'
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'inventory_report_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@reports_bp.route('/api/sales-chart')
@login_required
@admin_required
def sales_chart_data():
    # Get sales data for chart
    days = int(request.args.get('days', 7))
    start_date = datetime.now() - timedelta(days=days)
    
    sales_data = []
    current_date = start_date
    while current_date <= datetime.now():
        next_date = current_date + timedelta(days=1)
        daily_sales = Sale.query.filter(
            Sale.created_at >= current_date,
            Sale.created_at < next_date,
            Sale.status == 'completed'
        ).count()
        daily_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter(
            Sale.created_at >= current_date,
            Sale.created_at < next_date,
            Sale.status == 'completed'
        ).scalar() or 0
        
        sales_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'sales': daily_sales,
            'revenue': float(daily_revenue)
        })
        current_date = next_date
    
    return jsonify(sales_data)
