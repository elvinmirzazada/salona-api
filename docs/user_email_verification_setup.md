# User Email Verification Setup Guide

## Overview

This guide explains how to configure and use the email verification system for user signups in the Salona API. The system is designed to work for both Users (business professionals) and Customers, but currently only implemented for Users.

## Features

- ✅ Automatic email verification on user signup
- ✅ Secure token-based verification (24-hour expiration)
- ✅ HTML email templates with responsive design
- ✅ Password reset functionality (ready to extend)
- ✅ SMTP configuration support
- ✅ Generic service that works for both Users and Customers
- ✅ Separate verification tables for Users and Customers

## Architecture

### Components

1. **Email Service** (`app/services/email_service.py`)
   - Generic service that works for both users and customers
   - Handles sending emails via SMTP
   - Provides email templates for verification and password reset
   - Manages verification token creation with `entity_type` parameter

2. **User Endpoint** (`app/api/api_v1/endpoints/users.py`)
   - `/auth/signup` - Creates user and sends verification email
   - `/auth/verify_email` - Verifies email using token

3. **User CRUD** (`app/services/crud/user.py`)
   - Creates and validates verification tokens
   - Updates user email_verified status

4. **Database Models** (`app/models/models.py`)
   - `UserVerifications` table for user email verification
   - `CustomerVerifications` table for customer email verification (not currently used)

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

## Database Setup

Run the migration to create the `user_verifications` table:

```bash
alembic upgrade head
```

The migration creates the following table:

```sql
CREATE TABLE user_verifications (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,  -- 'EMAIL', 'PHONE', 'PASSWORD_RESET'
    status VARCHAR(50) DEFAULT 'PENDING',  -- 'PENDING', 'VERIFIED', 'EXPIRED'
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    used_at TIMESTAMP
);
```

## API Endpoints

### 1. User Signup

**POST** `/api/v1/users/auth/signup`

Creates a new user account and sends a verification email.

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
  "message": "User created successfully. Please check your email to verify your account."
}
```

### 2. Verify Email

**POST** `/api/v1/users/auth/verify_email`

Verifies the user's email using the token sent via email.

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
   - User submits registration form
   - System creates account with `email_verified: false`
   - System generates verification token (24-hour expiration)
   - System sends verification email

2. **Email Sent**
   - User receives email with verification link
   - Link format: `https://salona.me/verify-email?token={token}`

3. **User Clicks Link**
   - Frontend extracts token from URL
   - Frontend calls `/auth/verify_email` endpoint

4. **Verification Complete**
   - System validates token
   - System updates `email_verified: true`
   - System marks token as used
   - User can now fully access the platform

## Using the Email Service Programmatically

### For Users

```python
from app.services.email_service import email_service, create_verification_token
from app.models.enums import VerificationType

# Create verification token for a user
verification_record = create_verification_token(
    db=db,
    entity_id=user.id,
    verification_type=VerificationType.EMAIL,
    entity_type="user",  # Important: specify "user"
    expires_in_hours=24
)

# Send verification email
email_sent = email_service.send_verification_email(
    to_email=user.email,
    verification_token=verification_record.token,
    user_name=f"{user.first_name} {user.last_name}"
)
```

### For Customers (when needed)

```python
# Create verification token for a customer
verification_record = create_verification_token(
    db=db,
    entity_id=customer.id,
    verification_type=VerificationType.EMAIL,
    entity_type="customer",  # Important: specify "customer"
    expires_in_hours=24
)

# Send verification email (same method works for both)
email_sent = email_service.send_verification_email(
    to_email=customer.email,
    verification_token=verification_record.token,
    user_name=f"{customer.first_name} {customer.last_name}"
)
```

### Password Reset (ready to use)

```python
# Create password reset token
reset_record = create_verification_token(
    db=db,
    entity_id=user.id,
    verification_type=VerificationType.PASSWORD_RESET,
    entity_type="user",
    expires_in_hours=1  # Password reset expires in 1 hour
)

# Send password reset email
email_sent = email_service.send_password_reset_email(
    to_email=user.email,
    reset_token=reset_record.token,
    user_name=f"{user.first_name} {user.last_name}"
)
```

## Email Templates

### Verification Email

The verification email includes:
- Personalized greeting with user name
- Clear call-to-action button
- Alternative text link for accessibility
- 24-hour expiration notice
- Professional branding

### Password Reset Email (Ready to Use)

The password reset email includes:
- Personalized greeting
- Security warning
- Clear call-to-action button
- 1-hour expiration notice
- Professional branding

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
# 1. Create a user
curl -X POST http://localhost:8000/api/v1/users/auth/signup \
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
curl -X POST http://localhost:8000/api/v1/users/auth/verify_email \
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
6. **Database Cleanup**: Consider implementing a cleanup job for expired tokens

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
- [ ] Password reset functionality (service already built)
- [ ] Email change verification
- [ ] Configurable token expiration time
- [ ] Email templates customization via admin panel
- [ ] Email delivery tracking
- [ ] Multi-language support
- [ ] Rate limiting for email sending

## Extending to Customers

To enable email verification for customers in the future:

1. Update `app/api/api_v1/endpoints/customers.py` signup endpoint
2. Add verification endpoint for customers
3. Use the same `email_service` with `entity_type="customer"`
4. The service is already generic and ready to use!

Example:
```python
# In customer signup
verification_record = create_verification_token(
    db=db,
    entity_id=new_customer.id,
    verification_type=VerificationType.EMAIL,
    entity_type="customer",  # Use "customer" instead of "user"
    expires_in_hours=24
)
```

## Support

For issues or questions, please contact the development team or create an issue in the repository.

