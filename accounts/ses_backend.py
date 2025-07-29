"""
AWS SES Email Backend for Django using boto3
"""

import boto3
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMessage
from django.conf import settings
from botocore.exceptions import BotoCoreError, ClientError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("accounts")


class SESEmailBackend(BaseEmailBackend):
    """
    Custom Django email backend for AWS SES using boto3
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.ses_client = None
        self._setup_ses_client()

    def _setup_ses_client(self):
        """Initialize the SES client"""
        try:
            self.ses_client = boto3.client(
                "ses",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_SES_REGION_NAME,
            )
            logger.info(
                f"SES client initialized for region: {settings.AWS_SES_REGION_NAME}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize SES client: {e}")
            if not self.fail_silently:
                raise

    def send_messages(self, email_messages):
        """
        Send a list of EmailMessage objects.
        Returns the number of successfully sent messages.
        """
        if not self.ses_client:
            logger.error("SES client not initialized")
            return 0

        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send_message(message):
                sent_count += 1

        return sent_count

    def _send_message(self, message):
        """
        Send a single EmailMessage using SES
        """
        try:
            # Prepare message data
            destination = {
                "ToAddresses": message.to,
            }

            if message.cc:
                destination["CcAddresses"] = message.cc

            if message.bcc:
                destination["BccAddresses"] = message.bcc

            # Prepare message content
            message_data = {"Subject": {"Data": message.subject, "Charset": "UTF-8"}}

            # Handle both plain text and HTML content
            if hasattr(message, "alternatives") and message.alternatives:
                # Message has HTML alternative
                html_content = None
                for content, content_type in message.alternatives:
                    if content_type == "text/html":
                        html_content = content
                        break

                if html_content:
                    message_data["Body"] = {
                        "Text": {"Data": message.body, "Charset": "UTF-8"},
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                    }
                else:
                    message_data["Body"] = {
                        "Text": {"Data": message.body, "Charset": "UTF-8"}
                    }
            else:
                # Plain text only
                message_data["Body"] = {
                    "Text": {"Data": message.body, "Charset": "UTF-8"}
                }

            # Send the email
            response = self.ses_client.send_email(
                Source=message.from_email, Destination=destination, Message=message_data
            )

            message_id = response.get("MessageId")
            logger.info(f"Email sent successfully. SES Message ID: {message_id}")
            logger.info(f"Email sent to: {', '.join(message.to)}")

            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(f"SES ClientError ({error_code}): {error_message}")

            # Handle specific SES errors
            if error_code == "MessageRejected":
                logger.error(
                    "Message was rejected by SES. Check your sending domain and email content."
                )
            elif error_code == "MailFromDomainNotVerifiedException":
                logger.error(
                    "The domain used in the 'From' address is not verified with SES."
                )
            elif error_code == "ConfigurationSetDoesNotExistException":
                logger.error("The specified configuration set does not exist.")
            elif error_code == "SendingPausedException":
                logger.error("Email sending is paused for your account.")

            if not self.fail_silently:
                raise
            return False

        except BotoCoreError as e:
            logger.error(f"SES BotoCoreError: {e}")
            if not self.fail_silently:
                raise
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            if not self.fail_silently:
                raise
            return False

    def test_connection(self):
        """
        Test the SES connection and return quota information
        """
        try:
            if not self.ses_client:
                return {"error": "SES client not initialized"}

            # Get sending quota
            quota_response = self.ses_client.get_send_quota()

            # Get sending statistics
            stats_response = self.ses_client.get_send_statistics()

            return {
                "status": "connected",
                "max_24_hour_send": quota_response.get("Max24HourSend", 0),
                "max_send_rate": quota_response.get("MaxSendRate", 0),
                "sent_last_24_hours": quota_response.get("SentLast24Hours", 0),
                "region": settings.AWS_SES_REGION_NAME,
                "statistics_available": len(stats_response.get("SendDataPoints", [])),
            }

        except Exception as e:
            logger.error(f"SES connection test failed: {e}")
            return {"error": str(e)}
