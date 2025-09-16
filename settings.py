from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import db, BusinessSettings, User, UserActivityLog, BackupLog
from datetime import datetime
import os
import json
import shutil
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import shutil
import zipfile

settings_bp = Blueprint('settings', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@settings_bp.route('/business-profile', methods=['GET', 'POST'])
@login_required
@admin_required
def business_profile():
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
        settings.contact_email = request.form.get('contact_email')
        
        # Handle logo upload
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename:
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(os.getcwd(), 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save logo file
                logo_filename = f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                logo_path = os.path.join(upload_dir, logo_filename)
                logo_file.save(logo_path)
                
                # Update logo path in database
                settings.logo_path = f"uploads/{logo_filename}"
        
        db.session.commit()
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action="Updated business profile"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Business profile updated successfully!', 'success')
        return redirect(url_for('settings.business_profile'))
    
    return render_template('settings/business_profile.html', settings=settings)

@settings_bp.route('/system-settings')
@login_required
@admin_required
def system_settings():
    settings = BusinessSettings.query.first()
    if not settings:
        settings = BusinessSettings()
        db.session.add(settings)
        db.session.commit()
    
    return render_template('settings/system_settings.html', settings=settings)

@settings_bp.route('/update-system-settings', methods=['POST'])
@login_required
@admin_required
def update_system_settings():
    settings = BusinessSettings.query.first()
    if not settings:
        settings = BusinessSettings()
        db.session.add(settings)
    
    # Update system settings
    settings.timezone = request.form.get('timezone', 'UTC')
    settings.date_format = request.form.get('date_format', 'DD/MM/YYYY')
    settings.decimal_places = int(request.form.get('decimal_places', 2))
    settings.opening_time = request.form.get('opening_time', '09:00')
    settings.closing_time = request.form.get('closing_time', '17:00')
    
    # Update notification settings
    settings.low_stock_alerts = 'low_stock_alerts' in request.form
    settings.daily_sales_reports = 'daily_sales_reports' in request.form
    settings.system_maintenance_alerts = 'system_maintenance_alerts' in request.form
    
    # Update security settings
    settings.session_timeout = int(request.form.get('session_timeout', 30))
    settings.min_password_length = int(request.form.get('min_password_length', 6))
    settings.require_uppercase = 'require_uppercase' in request.form
    settings.require_lowercase = 'require_lowercase' in request.form
    settings.require_numbers = 'require_numbers' in request.form
    settings.require_special_chars = 'require_special_chars' in request.form
    settings.two_factor_enabled = 'two_factor_enabled' in request.form
    settings.activity_logging = 'activity_logging' in request.form
    
    db.session.commit()
    
    # Log activity
    activity = UserActivityLog(
        user_id=current_user.id,
        action="Updated system settings"
    )
    db.session.add(activity)
    db.session.commit()
    
    flash('System settings updated successfully!', 'success')
    return redirect(url_for('settings.system_settings'))

@settings_bp.route('/backup')
@login_required
@admin_required
def backup():
    # Get backup history
    backups = BackupLog.query.order_by(BackupLog.backup_date.desc()).all()
    return render_template('settings/backup.html', backups=backups)

@settings_bp.route('/backup/create')
@login_required
@admin_required
def create_backup():
    try:
        # Create backup directory
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"pos_backup_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create ZIP file
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database file
            db_path = os.path.join(os.getcwd(), 'pos_system.db')
            if os.path.exists(db_path):
                zipf.write(db_path, 'database/pos_system.db')
            
            # Add static files
            static_dir = os.path.join(os.getcwd(), 'static')
            if os.path.exists(static_dir):
                for root, dirs, files in os.walk(static_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, static_dir)
                        zipf.write(file_path, f'static/{arcname}')
            
            # Add templates
            templates_dir = os.path.join(os.getcwd(), 'templates')
            if os.path.exists(templates_dir):
                for root, dirs, files in os.walk(templates_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, templates_dir)
                        zipf.write(file_path, f'templates/{arcname}')
        
        # Record backup in database
        backup_log = BackupLog(
            file_path=backup_path,
            created_by=current_user.id
        )
        db.session.add(backup_log)
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Created backup: {backup_filename}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'Backup created successfully: {backup_filename}', 'success')
        
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'error')
    
    return redirect(url_for('settings.backup'))

@settings_bp.route('/backup/download/<int:backup_id>')
@login_required
@admin_required
def download_backup(backup_id):
    backup = BackupLog.query.get_or_404(backup_id)
    
    if os.path.exists(backup.file_path):
        from flask import send_file
        return send_file(
            backup.file_path,
            as_attachment=True,
            download_name=os.path.basename(backup.file_path)
        )
    else:
        flash('Backup file not found', 'error')
        return redirect(url_for('settings.backup'))

@settings_bp.route('/backup/restore', methods=['GET', 'POST'])
@login_required
@admin_required
def restore_backup():
    if request.method == 'POST':
        if 'backup_file' not in request.files:
            flash('No backup file selected', 'error')
            return redirect(url_for('settings.restore_backup'))
        
        backup_file = request.files['backup_file']
        if backup_file.filename == '':
            flash('No backup file selected', 'error')
            return redirect(url_for('settings.restore_backup'))
        
        try:
            # Create temporary directory for extraction
            temp_dir = os.path.join(os.getcwd(), 'temp_restore')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Extract backup
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Restore database
            db_backup_path = os.path.join(temp_dir, 'database', 'pos_system.db')
            if os.path.exists(db_backup_path):
                current_db_path = os.path.join(os.getcwd(), 'pos_system.db')
                shutil.copy2(db_backup_path, current_db_path)
            
            # Restore static files
            static_backup_dir = os.path.join(temp_dir, 'static')
            if os.path.exists(static_backup_dir):
                current_static_dir = os.path.join(os.getcwd(), 'static')
                if os.path.exists(current_static_dir):
                    shutil.rmtree(current_static_dir)
                shutil.copytree(static_backup_dir, current_static_dir)
            
            # Restore templates
            templates_backup_dir = os.path.join(temp_dir, 'templates')
            if os.path.exists(templates_backup_dir):
                current_templates_dir = os.path.join(os.getcwd(), 'templates')
                if os.path.exists(current_templates_dir):
                    shutil.rmtree(current_templates_dir)
                shutil.copytree(templates_backup_dir, current_templates_dir)
            
            # Clean up
            shutil.rmtree(temp_dir)
            
            # Log activity
            activity = UserActivityLog(
                user_id=current_user.id,
                action=f"Restored backup: {backup_file.filename}"
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Backup restored successfully! Please restart the application.', 'success')
            
        except Exception as e:
            flash(f'Restore failed: {str(e)}', 'error')
            # Clean up on error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    return render_template('settings/restore_backup.html')

@settings_bp.route('/backup/delete/<int:backup_id>')
@login_required
@admin_required
def delete_backup(backup_id):
    backup = BackupLog.query.get_or_404(backup_id)
    
    try:
        # Delete file
        if os.path.exists(backup.file_path):
            os.remove(backup.file_path)
        
        # Delete database record
        db.session.delete(backup)
        
        # Log activity
        activity = UserActivityLog(
            user_id=current_user.id,
            action=f"Deleted backup: {os.path.basename(backup.file_path)}"
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Backup deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Delete failed: {str(e)}', 'error')
    
    return redirect(url_for('settings.backup'))

@settings_bp.route('/email-test')
@login_required
@admin_required
def email_test():
    """Display email configuration test page"""
    return render_template('settings/email_test.html', config=current_app.config)

@settings_bp.route('/test-email', methods=['POST'])
@login_required
@admin_required
def test_email():
    """Send test email to verify configuration"""
    from email_utils import test_email_configuration
    
    success, message = test_email_configuration()
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('settings.email_test'))

@settings_bp.route('/api/system-info')
@login_required
@admin_required
def system_info():
    import platform
    import psutil
    
    info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'cpu_count': psutil.cpu_count(),
        'memory_total': psutil.virtual_memory().total,
        'memory_available': psutil.virtual_memory().available,
        'disk_usage': psutil.disk_usage('/').percent
    }
    
    return jsonify(info)
