# Point of Sale (POS) System

A comprehensive, modern Point of Sale system built with Flask, featuring a clean UI with Tailwind CSS and robust backend functionality.

## Features

### 🔐 User Management & Security
- **Role-Based Access Control**: Admin and Staff roles with different permissions
- **Secure Authentication**: Flask-Login with password hashing
- **User Activity Logging**: Track all user actions for audit purposes
- **Password Management**: Secure password change functionality

### 🛒 Sales & Checkout
- **Modern POS Interface**: Clean, responsive design optimized for touch devices
- **Product Search**: Search by name, SKU, barcode, or category
- **Shopping Cart**: Add, remove, and adjust quantities
- **Multiple Payment Methods**: Cash, card, mobile money, split payments
- **Hold/Resume Sales**: Pause sales and resume later
- **Refund Processing**: Handle returns and refunds
- **Digital Receipts**: Generate and print receipts

### 📦 Inventory Management
- **Product Management**: Full CRUD operations for products
- **Stock Tracking**: Real-time inventory monitoring
- **Low Stock Alerts**: Automatic notifications for low inventory
- **Stock Adjustments**: Handle damaged, returned, or manual adjustments
- **Category Management**: Organize products by categories
- **Supplier Integration**: Link products to suppliers

### 👥 Customer Management
- **Customer Records**: Store customer information and contact details
- **Credit Sales**: Track customer credit balances
- **Payment Tracking**: Record payments against credit balances
- **Sales History**: View customer purchase history

### 🚚 Supplier & Purchase Management
- **Supplier Records**: Maintain supplier information
- **Purchase Orders**: Create and manage stock replenishment orders
- **Order Status Tracking**: Pending, received, or cancelled
- **Cost Management**: Track product costs and margins

### 📊 Reports & Analytics
- **Sales Reports**: Daily, weekly, monthly sales data
- **Product Performance**: Best sellers and slow movers
- **Staff Performance**: Sales metrics by employee
- **Export Options**: PDF, CSV, and Excel formats
- **Interactive Charts**: Visual data representation

### ⚙️ System Settings
- **Business Profile**: Company name, logo, contact information
- **Tax Configuration**: Set tax rates and rules
- **Currency Settings**: Support for multiple currencies
- **Backup & Restore**: Local and cloud backup options
- **System Monitoring**: Performance and health checks

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (development), PostgreSQL/MySQL (production)
- **ORM**: SQLAlchemy with Flask-Migrate
- **Frontend**: Tailwind CSS, Alpine.js, Chart.js
- **Authentication**: Flask-Login
- **File Handling**: Pillow for image processing
- **Reports**: ReportLab for PDF generation, openpyxl for Excel

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pos-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   # Create .env file
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///pos_system.db
   ```

5. **Initialize database**
   ```bash
   python app.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

The system will be available at `http://localhost:5000`

### Default Admin Account
- **Username**: admin
- **Password**: admin123

**Important**: Change the default password immediately after first login!

## Usage

### For Administrators

1. **Dashboard**: View business overview, statistics, and recent activities
2. **User Management**: Create, edit, and manage staff accounts
3. **Inventory Control**: Add products, manage stock, and track suppliers
4. **Reports**: Generate sales reports, analyze performance, and export data
5. **System Settings**: Configure business profile, tax rates, and backup options

### For Staff

1. **POS Operations**: Process sales, handle payments, and generate receipts
2. **Product Search**: Quickly find products by name, SKU, or barcode
3. **Customer Service**: Handle customer inquiries and credit sales
4. **Stock Monitoring**: Check product availability and low stock alerts

## Database Schema

The system uses a comprehensive database design with the following main entities:

- **Users**: Staff accounts with role-based permissions
- **Products**: Inventory items with pricing and stock information
- **Sales**: Transaction records with items and payment details
- **Customers**: Customer information and credit management
- **Suppliers**: Vendor information and purchase order management
- **System Settings**: Business configuration and preferences

## API Endpoints

### Authentication
- `POST /login` - User login
- `GET /logout` - User logout
- `POST /change-password` - Change user password

### Sales
- `GET /sales/pos` - POS interface
- `POST /sales/api/cart/add` - Add item to cart
- `POST /sales/checkout` - Process sale
- `GET /sales/receipt/<id>` - View receipt

### Inventory
- `GET /inventory/products` - List products
- `POST /inventory/products/create` - Create product
- `PUT /inventory/products/<id>/edit` - Edit product
- `DELETE /inventory/products/<id>` - Delete product

### Reports
- `GET /reports/dashboard` - Analytics dashboard
- `GET /reports/sales-report` - Sales reports
- `GET /reports/export/sales-csv` - Export sales data

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `dev-secret-key-change-in-production` |
| `DATABASE_URL` | Database connection string | `sqlite:///pos_system.db` |
| `FLASK_ENV` | Flask environment | `development` |

### Database Configuration

For production, update the `DATABASE_URL` in your environment:

```bash
# PostgreSQL
DATABASE_URL=postgresql://username:password@localhost/pos_db

# MySQL
DATABASE_URL=mysql://username:password@localhost/pos_db
```

## Security Features

- **Password Hashing**: Secure password storage using bcrypt
- **Session Management**: Secure session handling with Flask-Login
- **CSRF Protection**: Built-in CSRF protection for forms
- **Input Validation**: Comprehensive input sanitization
- **Access Control**: Role-based permission system
- **Activity Logging**: Audit trail for all system actions

## Backup & Recovery

The system includes built-in backup functionality:

- **Local Backups**: Create compressed backups of database and files
- **Backup History**: Track all backup operations
- **Restore Functionality**: Restore from backup files
- **Automated Cleanup**: Manage backup storage

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue in the repository
- Check the documentation
- Review the code examples

## Roadmap

### Planned Features
- **Mobile App**: Native mobile applications for iOS and Android
- **Advanced Analytics**: Machine learning insights and predictions
- **Multi-location Support**: Manage multiple store locations
- **Integration APIs**: Connect with accounting and e-commerce platforms
- **Advanced Reporting**: Custom report builder and scheduling

### Performance Improvements
- **Caching**: Redis integration for improved performance
- **Database Optimization**: Query optimization and indexing
- **Async Processing**: Background task processing
- **CDN Integration**: Static file delivery optimization

---

**Note**: This is a production-ready POS system designed for small to medium businesses. Always test thoroughly in your environment before deploying to production.
