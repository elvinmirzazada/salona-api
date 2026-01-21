import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from sqlalchemy.orm import Session
from mailersend import MailerSendClient, EmailBuilder
from icalendar import Calendar, Event as ICalEvent

from app.core.config import settings
from app.models.models import CustomerVerifications, UserVerifications
from app.models.enums import VerificationType, VerificationStatus


class EmailService:
    """Service for sending emails via MailerSend - works for both users and customers"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ):
        self.api_key = api_key or getattr(settings, 'MAILERSEND_API_KEY', '')
        self.from_email = from_email or getattr(settings, 'MAILERSEND_FROM_EMAIL', '')
        self.from_name = from_name or getattr(settings, 'MAILERSEND_FROM_NAME', 'Salona')

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[list] = None
    ) -> bool:
        """
        Send an email via MailerSend

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text fallback content
            attachments: List of attachment dicts with 'content', 'filename', and 'content_type'

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Validate API key
            if not self.api_key:
                print("Error: MailerSend API key is not configured")
                return False

            # Create MailerSend client
            client = MailerSendClient(self.api_key)

            # Build email using EmailBuilder
            email_builder = (EmailBuilder()
                     .from_email(self.from_email, self.from_name)
                     .to_many([{"email": to_email, "name": "Recipient"}])
                     .subject(subject)
                     .html(html_content)
                     .text(text_content))

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    email_builder.attach_content(
                        content=attachment['content'],
                        filename=attachment['filename']
                    )

            email = email_builder.build()

            # Send email using MailerSend API
            response = client.emails.send(email)

            # Check if email was sent successfully
            # MailerSend returns None on success, raises exception on failure
            return True

        except Exception as e:
            print(f"Error sending email via MailerSend: {str(e)}")
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
        invitation_url = f"{settings.FRONTEND_URL}/users/accept-invitation?token={invitation_token}"

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

    def send_booking_notification_email(
        self,
        to_email: str,
        staff_name: str,
        customer_name: str,
        company_name: str,
        booking_date: str,
        services: list,
        booking_notes: Optional[str] = None
    ) -> bool:
        """
        Send booking notification email to staff members

        Args:
            to_email: Staff member's email address
            staff_name: Staff member's name
            customer_name: Customer's name who made the booking
            company_name: Company name
            booking_date: Date of the booking (formatted string)
            services: List of service names for the booking
            booking_notes: Optional notes from the customer

        Returns:
            bool: True if email sent successfully
        """
        subject = f"New Booking Notification - {company_name}"

        # Format services list for display
        services_html = ""
        if services:
            services_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
            for service in services:
                services_html += f"<li style='margin: 5px 0;'>{service}</li>"
            services_html += "</ul>"

        # Add notes section if provided
        notes_html = ""
        if booking_notes:
            notes_html = f"""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <strong style="color: #856404;">Customer Notes:</strong>
                <p style="margin: 10px 0 0 0; color: #856404;">{booking_notes}</p>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">New Booking Notification</h1>
                
                <p>Hi {staff_name},</p>
                
                <p>You have a new booking appointment scheduled at <strong>{company_name}</strong>.</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #007bff; margin-top: 0; font-size: 18px;">Booking Details</h2>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                                <strong>Customer:</strong>
                            </td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                                {customer_name}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                                <strong>Date:</strong>
                            </td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                                {booking_date}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;" colspan="2">
                                <strong>Services:</strong>
                                {services_html}
                            </td>
                        </tr>
                    </table>
                </div>
                
                {notes_html}
                
                <p style="color: #28a745; font-weight: bold;">Please make sure you're available at the scheduled time.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.FRONTEND_URL}/bookings" 
                       style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        View Booking
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center;">
                    © {datetime.now().year} Salona. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        services_text = "\n".join([f"  - {service}" for service in services]) if services else "  No services specified"
        notes_text = f"\n\nCustomer Notes:\n{booking_notes}\n" if booking_notes else ""

        text_content = f"""
        New Booking Notification
        
        Hi {staff_name},
        
        You have a new booking appointment scheduled at {company_name}.
        
        Booking Details:
        ----------------
        Customer: {customer_name}
        Date: {booking_date}
        
        Services:
        {services_text}
        {notes_text}
        
        Please make sure you're available at the scheduled time.
        
        View your bookings at: {settings.FRONTEND_URL}/bookings
        
        © {datetime.now().year} Salona. All rights reserved.
        """

        return self._send_email(to_email, subject, html_content, text_content)

    def send_booking_request_to_business_email(
        self,
        to_email: str,
        staff_name: str,
        customer_name: str,
        company_name: str,
        booking_date: str,
        services: list,
        booking_notes: Optional[str] = None,
        booking_id: Optional[str] = None
    ) -> bool:
        """
        Send booking request email to business owner/admin for confirmation or cancellation

        Args:
            to_email: Business owner/admin email address
            staff_name: Business owner/admin name
            customer_name: Customer's name who made the booking
            company_name: Company name
            booking_date: Date of the booking (formatted string)
            services: List of service names for the booking
            booking_notes: Optional notes from the customer
            booking_id: Booking ID for action links

        Returns:
            bool: True if email sent successfully
        """
        subject = f"New Booking Request - {company_name}"

        # Format services list for display
        services_html = ""
        if services:
            services_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
            for service in services:
                services_html += f"<li style='margin: 5px 0;'>{service}</li>"
            services_html += "</ul>"

        # Add notes section if provided
        notes_html = ""
        if booking_notes:
            notes_html = f"""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <strong style="color: #856404;">Customer Notes:</strong>
                <p style="margin: 10px 0 0 0; color: #856404;">{booking_notes}</p>
            </div>
            """

        # Action buttons
        action_buttons = ""
        # if booking_id:
        #     confirm_url = f"{settings.FRONTEND_URL}/bookings/{booking_id}/confirm"
        #     cancel_url = f"{settings.FRONTEND_URL}/bookings/{booking_id}/cancel"
        #     action_buttons = f"""
        #     <div style="text-align: center; margin: 30px 0;">
        #         <a href="{confirm_url}"
        #            style="background-color: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; margin: 0 10px;">
        #             Confirm Booking
        #         </a>
        #         <a href="{cancel_url}"
        #            style="background-color: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; margin: 0 10px;">
        #             Cancel Booking
        #         </a>
        #     </div>
        #     """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">New Booking Request</h1>
                
                <p>Hi {staff_name},</p>
                
                <p>You have received a new booking request for <strong>{company_name}</strong>.</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #007bff; margin-top: 0; font-size: 18px;">Booking Details</h2>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                                <strong>Customer:</strong>
                            </td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                                {customer_name}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                                <strong>Date:</strong>
                            </td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                                {booking_date}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;" colspan="2">
                                <strong>Services:</strong>
                                {services_html}
                            </td>
                        </tr>
                    </table>
                </div>
                
                {notes_html}
                
                {action_buttons}
                
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{settings.FRONTEND_URL}/bookings" 
                       style="color: #007bff; text-decoration: none; font-size: 14px;">
                        Or view in dashboard →
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center;">
                    © {datetime.now().year} Salona. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        services_text = "\n".join([f"  - {service}" for service in services]) if services else "  No services specified"
        notes_text = f"\n\nCustomer Notes:\n{booking_notes}\n" if booking_notes else ""

        text_content = f"""
        New Booking Request
        
        Hi {staff_name},
        
        You have received a new booking request for {company_name}.
        
        Booking Details:
        ----------------
        Customer: {customer_name}
        Date: {booking_date}
        
        Services:
        {services_text}
        {notes_text}
        
        Please review and take action on this booking request.
        
        View your bookings at: {settings.FRONTEND_URL}/bookings
        
        © {datetime.now().year} Salona. All rights reserved.
        """

        return self._send_email(to_email, subject, html_content, text_content)

    def send_booking_confirmation_to_customer_email(
        self,
        to_email: str,
        customer_name: str,
        company_name: str,
        booking_date: str,
        services: list,
        total_price: Optional[float] = None,
        booking_notes: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        location: Optional[str] = None,
        booking_id: Optional[str] = None
    ) -> bool:
        """
        Send booking confirmation email to customer with Google Calendar invitation

        Args:
            to_email: Customer's email address
            customer_name: Customer's name
            company_name: Company name
            booking_date: Date of the booking (formatted string for display)
            services: List of service names for the booking
            total_price: Total price of the booking
            booking_notes: Optional notes from the customer
            start_datetime: Start datetime of the booking (for calendar)
            end_datetime: End datetime of the booking (for calendar)
            location: Location/address of the booking
            booking_id: Booking ID for action links

        Returns:
            bool: True if email sent successfully
        """
        subject = f"Booking Confirmed - {company_name}"

        # Format services list for display
        services_html = ""
        if services:
            services_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
            for service in services:
                services_html += f"<li style='margin: 5px 0;'>{service}</li>"
            services_html += "</ul>"

        # Add price section if provided
        price_html = ""
        if total_price is not None:
            price_html = f"""
            <tr>
                <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                    <strong>Total Price:</strong>
                </td>
                <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                    ${total_price:.2f}
                </td>
            </tr>
            """

        # Add notes section if provided
        notes_html = ""
        if booking_notes:
            notes_html = f"""
            <div style="background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff;">
                <strong style="color: #004085;">Your Notes:</strong>
                <p style="margin: 10px 0 0 0; color: #004085;">{booking_notes}</p>
            </div>
            """

        # Action buttons
        action_buttons = ""
        if booking_id:
            cancel_url = f"{settings.FRONTEND_URL}/bookings/{booking_id}/cancel"
            action_buttons = f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{cancel_url}"
                   style="background-color: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; margin: 0 10px;">
                    Cancel Booking
                </a>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="background-color: #28a745; color: white; padding: 10px 20px; border-radius: 50px; display: inline-block; font-weight: bold;">
                        ✓ CONFIRMED
                    </div>
                </div>
                
                <h1 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">Your Booking is Confirmed!</h1>
                
                <p>Hi {customer_name},</p>
                
                <p>Great news! Your booking with <strong>{company_name}</strong> has been confirmed.</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #28a745; margin-top: 0; font-size: 18px;">Booking Details</h2>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                                <strong>Date & Time:</strong>
                            </td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                                {booking_date}
                            </td>
                        </tr>
                        {price_html}
                        <tr>
                            <td style="padding: 10px 0;" colspan="2">
                                <strong>Services:</strong>
                                {services_html}
                            </td>
                        </tr>
                    </table>
                </div>
                
                {notes_html}
                
                <p style="color: #007bff; font-weight: bold;">You can cancel the booking though this button.</p>
                
                {action_buttons}
                
                <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #17a2b8;">
                    <p style="margin: 0; color: #0c5460;">
                        <strong>Important:</strong> Please arrive 5-10 minutes before your appointment time.
                    </p>
                </div>
                
                <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <p style="margin: 0; color: #155724;">
                        <strong>📅 Calendar Invitation:</strong> A calendar invitation (.ics file) is attached to this email. 
                        Click on it to add this appointment to your calendar (Google Calendar, Outlook, Apple Calendar, etc.).
                    </p>
                </div>
                
                <p style="text-align: center; margin: 20px 0;">
                    We look forward to seeing you!
                </p>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center;">
                    © {datetime.now().year} Salona. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        services_text = "\n".join([f"  - {service}" for service in services]) if services else "  No services specified"
        price_text = f"\nTotal Price: ${total_price:.2f}" if total_price is not None else ""
        notes_text = f"\n\nYour Notes:\n{booking_notes}\n" if booking_notes else ""

        text_content = f"""
        YOUR BOOKING IS CONFIRMED!
        
        Hi {customer_name},
        
        Great news! Your booking with {company_name} has been confirmed.
        
        Booking Details:
        ----------------
        Date & Time: {booking_date}{price_text}
        
        Services:
        {services_text}
        {notes_text}
        
        Important: Please arrive 5-10 minutes before your appointment time.
        
        📅 A calendar invitation (.ics file) is attached to this email. Click on it to add this appointment to your calendar.
        
        We look forward to seeing you!
        
        © {datetime.now().year} Salona. All rights reserved.
        """

        # Generate calendar invitation if datetime is provided
        attachments = None
        if start_datetime and end_datetime:
            # Create event description with services
            services_list = ", ".join(services) if services else "Booking"
            event_description = f"Booking at {company_name}\n\nServices: {services_list}"
            if booking_notes:
                event_description += f"\n\nNotes: {booking_notes}"

            # Generate calendar invitation
            ical_content = self._generate_calendar_invitation(
                event_title=f"Appointment at {company_name}",
                event_description=event_description,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location=location,
                organizer_email=self.from_email,
                attendee_email=to_email
            )

            attachments = [{
                'content': ical_content,
                'filename': 'booking_invitation.ics',
                'content_type': 'text/calendar; method=REQUEST'
            }]

        return self._send_email(to_email, subject, html_content, text_content, attachments)

    def send_booking_cancellation_to_customer_email(
        self,
        to_email: str,
        customer_name: str,
        company_name: str,
        booking_date: str,
        services: list,
        company_id: str,
        cancellation_reason: Optional[str] = None
    ) -> bool:
        """
        Send booking cancellation email to customer

        Args:
            to_email: Customer's email address
            customer_name: Customer's name
            company_name: Company name
            booking_date: Date of the booking (formatted string)
            services: List of service names for the booking
            cancellation_reason: Optional reason for cancellation
            company_id : Company ID for booking link
        Returns:
            bool: True if email sent successfully
        """
        subject = f"Booking Cancelled - {company_name}"

        # Format services list for display
        services_html = ""
        if services:
            services_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
            for service in services:
                services_html += f"<li style='margin: 5px 0;'>{service}</li>"
            services_html += "</ul>"

        # Add cancellation reason if provided
        reason_html = ""
        if cancellation_reason:
            reason_html = f"""
            <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
                <strong style="color: #721c24;">Cancellation Reason:</strong>
                <p style="margin: 10px 0 0 0; color: #721c24;">{cancellation_reason}</p>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="background-color: #dc3545; color: white; padding: 10px 20px; border-radius: 50px; display: inline-block; font-weight: bold;">
                        ✗ CANCELLED
                    </div>
                </div>
                
                <h1 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">Booking Cancelled</h1>
                
                <p>Hi {customer_name},</p>
                
                <p>Your booking with <strong>{company_name}</strong> has been cancelled.</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #dc3545; margin-top: 0; font-size: 18px;">Cancelled Booking Details</h2>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                                <strong>Date & Time:</strong>
                            </td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                                {booking_date}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;" colspan="2">
                                <strong>Services:</strong>
                                {services_html}
                            </td>
                        </tr>
                    </table>
                </div>
                
                {reason_html}
                
                <p>If you'd like to reschedule or book a new appointment, please visit our website or contact us.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.FRONTEND_URL}/customers/{company_id}" 
                       style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Book Again
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center;">
                    © {datetime.now().year} Salona. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        services_text = "\n".join([f"  - {service}" for service in services]) if services else "  No services specified"
        reason_text = f"\n\nCancellation Reason:\n{cancellation_reason}\n" if cancellation_reason else ""

        text_content = f"""
        BOOKING CANCELLED
        
        Hi {customer_name},
        
        Your booking with {company_name} has been cancelled.
        
        Cancelled Booking Details:
        --------------------------
        Date & Time: {booking_date}
        
        Services:
        {services_text}
        {reason_text}
        
        If you'd like to reschedule or book a new appointment, please visit our website or contact us.
        
        Book again at: {settings.FRONTEND_URL}/bookings/new
        
        © {datetime.now().year} Salona. All rights reserved.
        """

        return self._send_email(to_email, subject, html_content, text_content)

    def send_booking_completed_to_customer_email(
        self,
        to_email: str,
        customer_name: str,
        company_name: str,
        booking_date: str,
        services: list,
        total_price: Optional[float] = None
    ) -> bool:
        """
        Send booking completion email to customer

        Args:
            to_email: Customer's email address
            customer_name: Customer's name
            company_name: Company name
            booking_date: Date of the booking (formatted string)
            services: List of service names for the booking
            total_price: Total price of the booking

        Returns:
            bool: True if email sent successfully
        """
        subject = f"Thank You - Booking Completed at {company_name}"

        # Format services list for display
        services_html = ""
        if services:
            services_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
            for service in services:
                services_html += f"<li style='margin: 5px 0;'>{service}</li>"
            services_html += "</ul>"

        # Add price section if provided
        price_html = ""
        if total_price is not None:
            price_html = f"""
            <tr>
                <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                    <strong>Total Amount:</strong>
                </td>
                <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                    ${total_price:.2f}
                </td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="background-color: #17a2b8; color: white; padding: 10px 20px; border-radius: 50px; display: inline-block; font-weight: bold;">
                        ✓ COMPLETED
                    </div>
                </div>
                
                <h1 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">Thank You for Your Visit!</h1>
                
                <p>Hi {customer_name},</p>
                
                <p>Thank you for choosing <strong>{company_name}</strong>! We hope you enjoyed your experience.</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #17a2b8; margin-top: 0; font-size: 18px;">Completed Service Details</h2>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef;">
                                <strong>Date & Time:</strong>
                            </td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #e9ecef; text-align: right;">
                                {booking_date}
                            </td>
                        </tr>
                        {price_html}
                        <tr>
                            <td style="padding: 10px 0;" colspan="2">
                                <strong>Services Received:</strong>
                                {services_html}
                            </td>
                        </tr>
                    </table>
                </div>
                
                <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <p style="margin: 0; color: #155724;">
                        <strong>We'd love your feedback!</strong> Your review helps us improve and helps others discover our services.
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.FRONTEND_URL}/review" 
                       style="background-color: #ffc107; color: #212529; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; margin-bottom: 10px;">
                        Leave a Review
                    </a>
                    <br>
                    <a href="{settings.FRONTEND_URL}/bookings/new" 
                       style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Book Again
                    </a>
                </div>
                
                <p style="text-align: center; margin: 20px 0; color: #28a745; font-weight: bold;">
                    We look forward to serving you again soon!
                </p>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center;">
                    © {datetime.now().year} Salona. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        services_text = "\n".join([f"  - {service}" for service in services]) if services else "  No services specified"
        price_text = f"\nTotal Amount: ${total_price:.2f}" if total_price is not None else ""

        text_content = f"""
        THANK YOU FOR YOUR VISIT!
        
        Hi {customer_name},
        
        Thank you for choosing {company_name}! We hope you enjoyed your experience.
        
        Completed Service Details:
        --------------------------
        Date & Time: {booking_date}{price_text}
        
        Services Received:
        {services_text}
        
        We'd love your feedback! Your review helps us improve and helps others discover our services.
        
        Leave a review at: {settings.FRONTEND_URL}/review
        Book again at: {settings.FRONTEND_URL}/bookings/new
        
        We look forward to serving you again soon!
        
        © {datetime.now().year} Salona. All rights reserved.
        """

        return self._send_email(to_email, subject, html_content, text_content)

    @staticmethod
    def _generate_calendar_invitation(
        event_title: str,
        event_description: str,
        start_datetime: datetime,
        end_datetime: datetime,
        location: Optional[str] = None,
        organizer_email: Optional[str] = None,
        attendee_email: Optional[str] = None
    ) -> str:
        """
        Generate iCalendar format invitation

        Args:
            event_title: Title of the event
            event_description: Description of the event
            start_datetime: Start date and time (must be timezone-aware)
            end_datetime: End date and time (must be timezone-aware)
            location: Location of the event
            organizer_email: Email of the organizer
            attendee_email: Email of the attendee

        Returns:
            Base64 encoded iCalendar content
        """
        # Ensure datetime objects are timezone-aware
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        if end_datetime.tzinfo is None:
            end_datetime = end_datetime.replace(tzinfo=timezone.utc)

        cal = Calendar()
        cal.add('prodid', '-//Salona Booking System//salona.com//')
        cal.add('version', '2.0')
        cal.add('method', 'REQUEST') # Use REQUEST for invitations

        event = ICalEvent()
        event.add('uid', f'{uuid.uuid4()}@salona.com')
        event.add('summary', event_title)
        event.add('description', event_description)
        event.add('dtstart', start_datetime)
        event.add('dtend', end_datetime)
        event.add('dtstamp', datetime.now(timezone.utc))
        event.add('status', 'CONFIRMED')
        event.add('sequence', 0)

        if location:
            event.add('location', location)

        if organizer_email:
            event.add('organizer', f'mailto:{organizer_email}')

        if attendee_email:
            # Add attendee with proper parameters for better compatibility
            event.add('attendee', attendee_email, parameters={
                'CUTYPE': 'INDIVIDUAL',
                'ROLE': 'REQ-PARTICIPANT',
                'PARTSTAT': 'NEEDS-ACTION',
                'RSVP': 'TRUE'
            })

        cal.add_component(event)

        # Convert to bytes and then to base64
        return cal.to_ical()


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
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    
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
