"""
Email utility functions for the POS System
"""
from flask import current_app
from flask_mail import Message
from extensions import mail
import logging

def send_receipt_email(sale, pdf_buffer):
    """
    Send receipt email with PDF attachment
    
    Args:
        sale: Sale object
        pdf_buffer: BytesIO buffer containing PDF data
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not sale.customer or not sale.customer.email:
            return False, "Customer email not available"
        
        if not current_app.config.get('MAIL_USERNAME'):
            return False, "Email configuration not set up"
        
        # Get business settings
        from models import BusinessSettings
        business_settings = BusinessSettings.query.first()
        business_name = business_settings.business_name if business_settings else "POS System"
        sender_email = business_settings.contact_email if business_settings and business_settings.contact_email else current_app.config.get('MAIL_DEFAULT_SENDER')
        
        msg = Message(
            subject=f'Receipt #{sale.receipt.receipt_number} - {business_name}',
            sender=sender_email,
            recipients=[sale.customer.email]
        )
        
        msg.body = f"""Dear {sale.customer.name},

Thank you for your purchase! Please find your receipt attached.

Receipt Details:
- Receipt Number: {sale.receipt.receipt_number}
- Date: {sale.created_at.strftime('%d/%m/%Y %H:%M')}
- Total Amount: GH₵{sale.total_amount:.2f}
- Payment Method: {sale.payment_method.title()}

We appreciate your business!

Best regards,
{business_name}
{business_settings.address if business_settings and business_settings.address else ''}
{business_settings.contact if business_settings and business_settings.contact else ''}
        """
        
        # Attach PDF
        msg.attach(
            f"receipt_{sale.receipt.receipt_number}.pdf",
            "application/pdf",
            pdf_buffer.getvalue()
        )
        
        mail.send(msg)
        return True, f'Receipt emailed successfully to {sale.customer.email}!'
        
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

def send_receipt_email_to_address(sale, pdf_buffer, recipient_email, custom_message=""):
    """
    Send receipt PDF to any email address with optional custom message
    """
    try:
        from flask_mail import Message
        from extensions import mail
        from models import BusinessSettings
        
        # Get business settings for sender email
        business_settings = BusinessSettings.query.first()
        sender_email = current_app.config['MAIL_DEFAULT_SENDER']
        if business_settings and business_settings.contact_email:
            sender_email = business_settings.contact_email
        
        # Create email message
        subject = f"Receipt #{sale.receipt.receipt_number} - {business_settings.business_name if business_settings and business_settings.business_name else 'POS System'}"
        
        # Build email body
        body_parts = []
        
        if custom_message.strip():
            body_parts.append(custom_message.strip())
            body_parts.append("")  # Add blank line
        
        body_parts.extend([
            f"Dear Customer,",
            "",
            f"Thank you for your purchase! Please find your receipt attached.",
            "",
            f"Sale Details:",
            f"• Receipt Number: {sale.receipt.receipt_number}",
            f"• Date: {sale.created_at.strftime('%d/%m/%Y %H:%M')}",
            f"• Total Amount: GH₵{sale.total_amount:.2f}",
            f"• Payment Method: {sale.payment_method.replace('_', ' ').title()}",
            "",
            f"If you have any questions about this purchase, please contact us.",
            "",
            f"Best regards,",
            f"{business_settings.business_name if business_settings and business_settings.business_name else 'POS System Team'}"
        ])
        
        body = "\n".join(body_parts)
        
        msg = Message(
            subject=subject,
            sender=sender_email,
            recipients=[recipient_email],
            body=body
        )
        
        # Attach PDF
        pdf_buffer.seek(0)
        msg.attach(
            filename=f"receipt_{sale.receipt.receipt_number}.pdf",
            content_type="application/pdf",
            data=pdf_buffer.read()
        )
        
        mail.send(msg)
        return True, f"Receipt sent successfully to {recipient_email}"
        
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

def send_low_stock_alert(products):
    """
    Send low stock alert email to admin users
    
    Args:
        products: List of products with low stock
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not current_app.config.get('MAIL_USERNAME'):
            return False, "Email configuration not set up"
        
        from models import User, BusinessSettings
        admin_users = User.query.filter_by(role='admin', is_active=True).all()
        admin_emails = [user.email for user in admin_users if user.email]
        
        if not admin_emails:
            return False, "No admin email addresses found"
        
        business_settings = BusinessSettings.query.first()
        business_name = business_settings.business_name if business_settings else "POS System"
        sender_email = business_settings.contact_email if business_settings and business_settings.contact_email else current_app.config.get('MAIL_DEFAULT_SENDER')
        
        msg = Message(
            subject=f'Low Stock Alert - {business_name}',
            sender=sender_email,
            recipients=admin_emails
        )
        
        product_list = "\n".join([
            f"- {product.name} (SKU: {product.sku}): {product.stock_quantity} remaining"
            for product in products
        ])
        
        msg.body = f"""Low Stock Alert

The following products are running low on stock:

{product_list}

Please restock these items as soon as possible.

Best regards,
{business_name} System
        """
        
        mail.send(msg)
        return True, f'Low stock alert sent to {len(admin_emails)} admin(s)!'
        
    except Exception as e:
        logging.error(f"Error sending low stock alert: {str(e)}")
        return False, f'Error sending alert: {str(e)}'

def test_email_configuration():
    """
    Test email configuration by sending a test email
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not current_app.config.get('MAIL_USERNAME'):
            return False, "Email configuration not set up"
        
        from models import User
        admin_user = User.query.filter_by(role='admin', is_active=True).first()
        
        if not admin_user or not admin_user.email:
            return False, "No admin email address found"
        
        from models import BusinessSettings
        business_settings = BusinessSettings.query.first()
        sender_email = business_settings.contact_email if business_settings and business_settings.contact_email else current_app.config.get('MAIL_DEFAULT_SENDER')
        
        msg = Message(
            subject='POS System - Email Configuration Test',
            sender=sender_email,
            recipients=[admin_user.email]
        )
        
        msg.body = """This is a test email to verify that your POS System email configuration is working correctly.

If you receive this email, your email settings are properly configured!

Best regards,
POS System
        """
        
        mail.send(msg)
        return True, f'Test email sent successfully to {admin_user.email}!'
        
    except Exception as e:
        logging.error(f"Error sending test email: {str(e)}")
        return False, f'Error sending test email: {str(e)}'
