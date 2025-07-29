from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger("accounts")


def send_verification_email(user, token):
    """Send email verification email to user"""
    try:
        subject = "Verify your email address - Calorie Tracker"
        
        # Create verification URL (frontend URL)
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}"
        
        html_message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333; text-align: center;">Welcome to Calorie Tracker!</h2>
            <p>Hi {user.username},</p>
            <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background-color: #007bff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #666;">{verification_url}</p>
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                This verification link will expire in 24 hours. If you didn't create this account, 
                please ignore this email.
            </p>
        </div>
        """
        
        plain_message = f"""
        Welcome to Calorie Tracker!
        
        Hi {user.username},
        
        Thank you for signing up! Please verify your email address by clicking the link below:
        
        {verification_url}
        
        This verification link will expire in 24 hours. If you didn't create this account, 
        please ignore this email.
        """
        
        # Use EmailMultiAlternatives for better HTML support with SES
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Verification email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        return False


def send_password_reset_email(user, token):
    """Send password reset email to user"""
    try:
        subject = "Reset your password - Calorie Tracker"
        
        # Create reset URL (frontend URL)
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"
        
        html_message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333; text-align: center;">Password Reset Request</h2>
            <p>Hi {user.username},</p>
            <p>We received a request to reset your password. Click the button below to set a new password:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #dc3545; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #666;">{reset_url}</p>
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                This password reset link will expire in 1 hour. If you didn't request this reset, 
                please ignore this email - your password will remain unchanged.
            </p>
        </div>
        """
        
        plain_message = f"""
        Password Reset Request
        
        Hi {user.username},
        
        We received a request to reset your password. Click the link below to set a new password:
        
        {reset_url}
        
        This password reset link will expire in 1 hour. If you didn't request this reset, 
        please ignore this email - your password will remain unchanged.
        """
        
        # Use EmailMultiAlternatives for better HTML support with SES
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False