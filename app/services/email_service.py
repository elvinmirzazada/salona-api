import uuid
from datetime import datetime, timedelta
from typing import Optional, Union
from sqlalchemy.orm import Session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from app.core.config import settings
from app.models.models import CustomerVerifications, UserVerifications
from app.models.enums import VerificationType, VerificationStatus


class EmailService:
    """Service for sending emails via SendGrid - works for both users and customers"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ):
        self.api_key = api_key or getattr(settings, 'SENDGRID_API_KEY', '')
        self.from_email = from_email or getattr(settings, 'SENDGRID_FROM_EMAIL', '')
        self.from_name = from_name or getattr(settings, 'SENDGRID_FROM_NAME', 'Salona')

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email via SendGrid

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text fallback content
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Validate API key
            if not self.api_key:
                print("Error: SendGrid API key is not configured")
                return False

            # Create SendGrid message
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", text_content or ""),
                html_content=Content("text/html", html_content)
            )

            # Send email using SendGrid API
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)

            # Check if email was sent successfully (2xx status codes)
            if 200 <= response.status_code < 300:
                return True
            else:
                print(f"SendGrid API returned status code: {response.status_code}")
                return False

        except Exception as e:
            print(f"Error sending email via SendGrid: {str(e)}")
            return False
    
    def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        user_name: str
    ) -> bool:
        """
        Send email verification email (works for both users and customers)

        Args:
            to_email: Email address
            verification_token: Verification token
            user_name: User's name

        Returns:
            bool: True if email sent successfully
        """
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        subject = "Verify Your Email Address - Salona"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">Welcome to Salona!</h1>
                
                <p>Hi {user_name},</p>
                
                <p>Thank you for signing up! To complete your registration, please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Verify Email Address
                    </a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="background-color: #e9ecef; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {verification_url}
                </p>
                
                <p style="color: #6c757d; font-size: 14px; margin-top: 30px;">
                    This verification link will expire in 24 hours. If you didn't create an account with Salona, please ignore this email.
                </p>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center;">
                    © {datetime.now().year} Salona. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Salona!
        
        Hi {user_name},
        
        Thank you for signing up! To complete your registration, please verify your email address by clicking the link below:
        
        {verification_url}
        
        This verification link will expire in 24 hours. If you didn't create an account with Salona, please ignore this email.
        
        © {datetime.now().year} Salona. All rights reserved.
        """
        
        return self._send_email(to_email, subject, html_content, text_content)
    
    def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: str
    ) -> bool:
        """
        Send password reset email (works for both users and customers)

        Args:
            to_email: Email address
            reset_token: Password reset token
            user_name: User's name

        Returns:
            bool: True if email sent successfully
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        subject = "Reset Your Password - Salona"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">Password Reset Request</h1>
                
                <p>Hi {user_name},</p>
                
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="background-color: #e9ecef; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {reset_url}
                </p>
                
                <p style="color: #6c757d; font-size: 14px; margin-top: 30px;">
                    This password reset link will expire in 1 hour. If you didn't request a password reset, please ignore this email or contact support if you have concerns.
                </p>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center;">
                    © {datetime.now().year} Salona. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request
        
        Hi {user_name},
        
        We received a request to reset your password. Click the link below to create a new password:
        
        {reset_url}
        
        This password reset link will expire in 1 hour. If you didn't request a password reset, please ignore this email.
        
        © {datetime.now().year} Salona. All rights reserved.
        """
        
        return self._send_email(to_email, subject, html_content, text_content)

    def send_staff_invitation_email(
        self,
        to_email: str,
        invitation_token: str,
        invited_by: str,
        company_name: str,
        is_existing_user: bool = False
    ) -> bool:
        """
        Send staff member invitation email

        Args:
            to_email: Email address to invite
            invitation_token: Invitation token
            invited_by: Name of person sending invitation
            company_name: Company name
            is_existing_user: Whether the user already exists in the system

        Returns:
            bool: True if email sent successfully
        """
        invitation_url = f"{settings.FRONTEND_URL}/accept-invitation?token={invitation_token}"

        subject = f"You're Invited to Join {company_name} on Salona"

        if is_existing_user:
            # Email for existing users
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                    <h1 style="color: #2c3e50; margin-bottom: 20px;">You've Been Invited to Join a Team!</h1>
                    
                    <p>Hi there,</p>
                    
                    <p><strong>{invited_by}</strong> has invited you to join <strong>{company_name}</strong> on Salona as a staff member.</p>
                    
                    <p>To accept this invitation and start collaborating, click the button below:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_url}" 
                           style="background-color: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                            Accept Invitation
                        </a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="background-color: #e9ecef; padding: 10px; border-radius: 5px; word-break: break-all;">
                        {invitation_url}
                    </p>
                    
                    <p style="color: #6c757d; font-size: 14px; margin-top: 30px;">
                        This invitation will expire in 3 days. If you didn't expect this invitation, you can safely ignore this email.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                    
                    <p style="color: #6c757d; font-size: 12px; text-align: center;">
                        © {datetime.now().year} Salona. All rights reserved.
                    </p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            You've Been Invited to Join a Team!
            
            Hi there,
            
            {invited_by} has invited you to join {company_name} on Salona as a staff member.
            
            To accept this invitation and start collaborating, click the link below:
            
            {invitation_url}
            
            This invitation will expire in 3 days. If you didn't expect this invitation, you can safely ignore this email.
            
            © {datetime.now().year} Salona. All rights reserved.
            """
        else:
            # Email for new users
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                    <h1 style="color: #2c3e50; margin-bottom: 20px;">Welcome to Salona!</h1>
                    
                    <p>Hi there,</p>
                    
                    <p><strong>{invited_by}</strong> has invited you to join <strong>{company_name}</strong> on Salona as a staff member.</p>
                    
                    <p>To accept this invitation and create your account, click the button below:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_url}" 
                           style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                            Accept Invitation & Sign Up
                        </a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="background-color: #e9ecef; padding: 10px; border-radius: 5px; word-break: break-all;">
                        {invitation_url}
                    </p>
                    
                    <p style="color: #6c757d; font-size: 14px; margin-top: 30px;">
                        This invitation will expire in 3 days. Once you accept, you'll be able to create your account and get started with {company_name}.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                    
                    <p style="color: #6c757d; font-size: 12px; text-align: center;">
                        © {datetime.now().year} Salona. All rights reserved.
                    </p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Welcome to Salona!
            
            Hi there,
            
            {invited_by} has invited you to join {company_name} on Salona as a staff member.
            
            To accept this invitation and create your account, click the link below:
            
            {invitation_url}
            
            This invitation will expire in 3 days. Once you accept, you'll be able to create your account and get started with {company_name}.
            
            © {datetime.now().year} Salona. All rights reserved.
            """

        return self._send_email(to_email, subject, html_content, text_content)


def create_verification_token(
    db: Session,
    entity_id: str,
    verification_type: VerificationType,
    entity_type: str = "user",
    expires_in_hours: int = 24
) -> Union[UserVerifications, CustomerVerifications]:
    """
    Create a verification token for a user or customer

    Args:
        db: Database session
        entity_id: User or Customer ID
        verification_type: Type of verification (email, phone, etc.)
        entity_type: Either "user" or "customer"
        expires_in_hours: Hours until token expires
        
    Returns:
        UserVerifications or CustomerVerifications: The created verification record
    """
    token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(hours=expires_in_hours)
    
    if entity_type == "user":
        db_obj = UserVerifications(
            id=uuid.uuid4(),
            user_id=entity_id,
            token=token,
            type=verification_type,
            status=VerificationStatus.PENDING,
            expires_at=expires_at
        )
    else:  # customer
        db_obj = CustomerVerifications(
            id=uuid.uuid4(),
            customer_id=entity_id,
            token=token,
            type=verification_type,
            status=VerificationStatus.PENDING,
            expires_at=expires_at
        )

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    
    return db_obj


# Singleton instance
email_service = EmailService()
