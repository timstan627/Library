import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

# M10: an unbounded SMTP connect can hang a request thread forever; every
# socket must be closed even when the send fails mid-flight.
SMTP_TIMEOUT_SECONDS = 30

class EmailService:
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.sender = settings.emails_from_email or settings.smtp_user
        self.sender_name = settings.emails_from_name

    def _send_message(self, msg, to_email: str):
        """Send a prepared MIME message, closing the socket on any outcome."""
        if not self.smtp_user or not self.smtp_password:
            raise Exception("SMTP credentials not configured")

        with smtplib.SMTP(
            self.smtp_host, self.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
        ) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.sender, to_email, msg.as_string())

    def send_reset_password_email(self, to_email: str, token: str):
        """Send password reset email."""
        try:
            if not self.smtp_user:
                logger.warning("SMTP not configured, skipping email.")
                return

            reset_link = f"{settings.app_url}/auth/reset-password?token={token}"
            
            subject = f"Reset Your Password - {self.sender_name}"
            
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2>Reset Your Password</h2>
                        <p>Hello,</p>
                        <p>We received a request to reset your password for your Student Library account.</p>
                        <p>Click the button below to reset it:</p>
                        <a href="{reset_link}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; margin: 20px 0;">Reset Password</a>
                        <p>Or copy this link:</p>
                        <p>{reset_link}</p>
                        <p>If you didn't ask for this, you can ignore this email.</p>
                        <p>Best regards,<br>{self.sender_name}</p>
                    </div>
                </body>
            </html>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.sender}>"
            msg["To"] = to_email

            msg.attach(MIMEText(html_content, "html"))

            self._send_message(msg, to_email)
            
            logger.info(f"Reset email sent to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            # Don't crash the request logic, just log error
            
email_service = EmailService()
