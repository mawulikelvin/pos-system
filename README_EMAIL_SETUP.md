# Email Configuration for Render Deployment

## Quick Setup Guide

After deploying to Render, you need to configure email settings to enable receipt emails and notifications.

### 1. Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account Settings → Security
   - Under "2-Step Verification", click "App passwords"
   - Generate password for "Mail"
   - Copy the 16-character password

### 2. Configure Environment Variables in Render

In your Render dashboard:

1. Go to your web service settings
2. Navigate to "Environment" tab
3. Add these variables:

```
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-character-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

**Note**: The MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS are already configured in render.yaml

### 3. Test Email Configuration

1. Deploy your application
2. Login as admin
3. Go to Settings → Email Test
4. Click "Send Test Email"
5. Check your email for the test message

### 4. Email Features Available

- **Receipt Emails**: Customers receive PDF receipts via email
- **Low Stock Alerts**: Admins get notified when inventory is low
- **System Notifications**: Various system alerts and updates

### 5. Alternative Email Providers

For other email providers, update these environment variables:

**Outlook/Hotmail:**
```
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
```

**Yahoo:**
```
MAIL_SERVER=smtp.mail.yahoo.com
MAIL_PORT=587
MAIL_USE_TLS=True
```

**Custom SMTP:**
Contact your email provider for SMTP settings.

### 6. Troubleshooting

- Ensure 2FA is enabled for Gmail
- Use App Password, not your regular password
- Check spam folder for test emails
- Verify environment variables are set correctly in Render

### 7. Security Notes

- Never commit email passwords to your repository
- Use environment variables for all sensitive information
- Regularly rotate your app passwords
- Monitor email usage for suspicious activity
