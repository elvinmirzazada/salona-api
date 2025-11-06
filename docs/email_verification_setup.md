# Email Verification Setup Guide

## Overview

This guide explains how to configure and use the email verification system for customer signups in the Salona API.

## Features

- ✅ Automatic email verification on customer signup
- ✅ Secure token-based verification (24-hour expiration)
- ✅ HTML email templates with responsive design
- ✅ Password reset functionality (ready to extend)
- ✅ SMTP configuration support

## Architecture

### Components

1. **Email Service** (`app/services/email_service.py`)
   - Handles sending emails via SMTP
   - Provides email templates for verification and password reset
   - Manages verification token creation

2. **Customer Endpoint** (`app/api/api_v1/endpoints/customers.py`)
   - `/auth/signup` - Creates customer and sends verification email
   - `/auth/verify_email` - Verifies email using token

3. **Customer CRUD** (`app/services/crud/customer.py`)
   - Creates and validates verification tokens
   - Updates customer email_verified status

## Configuration

### Environment Variables

Add the following environment variables to your `.env` file or deployment platform:

```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com              # Your SMTP server
SMTP_PORT=587                         # SMTP port (587 for TLS, 465 for SSL)
SMTP_USER=your-email@gmail.com        # SMTP username
SMTP_PASSWORD=your-app-password       # SMTP password or app-specific password
SMTP_FROM_EMAIL=noreply@salona.me     # From email address (optional, defaults to SMTP_USER)
SMTP_FROM_NAME=Salona                 # From name (optional, defaults to "Salona")

# Frontend URL for verification links
FRONTEND_URL=https://salona.me
```

### SMTP Provider Examples

#### Gmail
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use App Password, not regular password
```

**Note**: For Gmail, you need to create an [App Password](https://support.google.com/accounts/answer/185833)

#### SendGrid
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@salona.me
```

#### AWS SES
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-aws-smtp-username
SMTP_PASSWORD=your-aws-smtp-password
SMTP_FROM_EMAIL=noreply@salona.me
```

#### Mailgun
```bash
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-smtp-password
SMTP_FROM_EMAIL=noreply@salona.me
```

## API Endpoints

### 1. Customer Signup

**POST** `/api/v1/customers/auth/signup`

Creates a new customer account and sends a verification email.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "password": "securePassword123",
  "phone": "+1234567890"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Customer created successfully. Please check your email to verify your account.",
  "data": {
    "id": "uuid-here",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "email_verified": false,
    "status": "pending_verification"
  }
}
```

### 2. Verify Email

**POST** `/api/v1/customers/auth/verify_email`

Verifies the customer's email using the token sent via email.

**Request Body:**
```json
{
  "token": "verification-token-from-email"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Email verified successfully"
}
```

**Error Responses:**
- `404 Not Found` - Token not found
- `400 Bad Request` - Token expired or invalid
- `500 Internal Server Error` - Verification process failed

## Workflow

1. **User Signs Up**
   - Customer submits registration form
   - System creates account with `email_verified: false`
   - System generates verification token (24-hour expiration)
   - System sends verification email

2. **Email Sent**
   - Customer receives email with verification link
   - Link format: `https://salona.me/verify-email?token={token}`

3. **User Clicks Link**
   - Frontend extracts token from URL
   - Frontend calls `/auth/verify_email` endpoint

4. **Verification Complete**
   - System validates token
   - System updates `email_verified: true`
   - System marks token as used
   - Customer can now fully access the platform

## Database Schema

### CustomerVerifications Table

```sql
CREATE TABLE customer_verifications (
    id UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,  -- 'EMAIL', 'PHONE', 'PASSWORD_RESET'
    status VARCHAR(50) DEFAULT 'PENDING',  -- 'PENDING', 'VERIFIED', 'EXPIRED'
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    used_at TIMESTAMP
);
```

## Email Templates

### Verification Email

The verification email includes:
- Personalized greeting with customer name
- Clear call-to-action button
- Alternative text link for accessibility
- 24-hour expiration notice
- Professional branding

### Password Reset Email (Ready to Use)

The system includes a password reset email template ready to be implemented:
```python
email_service.send_password_reset_email(
    to_email="customer@example.com",
    reset_token="reset-token",
    customer_name="John Doe"
)
```

## Testing

### Local Testing with MailHog

For local development, you can use [MailHog](https://github.com/mailhog/MailHog):

```bash
# Start MailHog
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Configure .env
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
```

Then view emails at: http://localhost:8025

### Manual Testing

```bash
# 1. Create a customer
curl -X POST http://localhost:8000/api/v1/customers/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "password": "password123",
    "phone": "+1234567890"
  }'

# 2. Check email for verification token

# 3. Verify email
curl -X POST http://localhost:8000/api/v1/customers/auth/verify_email \
  -H "Content-Type: application/json" \
  -d '{
    "token": "token-from-email"
  }'
```

## Security Considerations

1. **Token Expiration**: Tokens expire after 24 hours
2. **One-time Use**: Tokens can only be used once
3. **Secure Transport**: Emails sent over TLS/SSL
4. **Password Hashing**: Passwords are hashed with bcrypt
5. **No Sensitive Data**: Tokens don't contain user data

## Troubleshooting

### Email Not Sending

1. **Check SMTP credentials**: Verify username and password
2. **Check firewall**: Ensure port 587/465 is not blocked
3. **Check logs**: Look for error messages in application logs
4. **Test SMTP connection**: Use a tool like `telnet` to test connectivity

### Email Goes to Spam

1. **SPF Records**: Configure SPF records for your domain
2. **DKIM**: Set up DKIM signing
3. **From Address**: Use a verified domain email address
4. **Content**: Avoid spam trigger words

### Token Expired

- Tokens expire after 24 hours
- User needs to request a new verification email
- Consider implementing a "resend verification email" endpoint

## Future Enhancements

- [ ] Resend verification email endpoint
- [ ] Password reset functionality
- [ ] Email change verification
- [ ] Configurable token expiration time
- [ ] Email templates customization via admin panel
- [ ] Email delivery tracking
- [ ] Multi-language support

## Support

For issues or questions, please contact the development team or create an issue in the repository.

