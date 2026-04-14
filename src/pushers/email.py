"""Email push channel implementation."""

import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

import requests

from config import settings


class EmailPusher:
    """Send reports via email using SMTP or Resend API."""

    def __init__(
        self,
        use_resend: bool = False,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        resend_api_key: Optional[str] = None,
    ):
        """Initialize email pusher.

        Args:
            use_resend: Use Resend API instead of SMTP
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_username: SMTP username
            smtp_password: SMTP password
            from_email: From email address
            resend_api_key: Resend API key
        """
        self.use_resend = use_resend or bool(settings.resend_api_key)

        # SMTP configuration - use parameter if provided, otherwise use settings
        self.smtp_host = smtp_host if smtp_host is not None else settings.smtp_host
        self.smtp_port = smtp_port if smtp_port is not None else settings.smtp_port
        self.smtp_username = smtp_username if smtp_username is not None else settings.smtp_username
        self.smtp_password = smtp_password if smtp_password is not None else settings.smtp_password
        self.from_email = from_email if from_email is not None else (settings.smtp_from_email or os.getenv("SMTP_FROM_EMAIL"))

        # Resend configuration
        self.resend_api_key = resend_api_key or settings.resend_api_key

        # Validate configuration
        if self.use_resend and not self.resend_api_key:
            raise ValueError("Resend API key is required when using Resend")
        if not self.use_resend and not self.smtp_host:
            raise ValueError("SMTP host is required when using SMTP")

    def send(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send email.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback content

        Returns:
            True if sent successfully, False otherwise
        """
        if self.use_resend:
            return self._send_via_resend(to_emails, subject, html_content, text_content)
        else:
            return self._send_via_smtp(to_emails, subject, html_content, text_content)

    def _send_via_resend(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send email via Resend API.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback content

        Returns:
            True if sent successfully
        """
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {self.resend_api_key}",
            "Content-Type": "application/json",
        }

        for to_email in to_emails:
            data = {
                "from": self.from_email or "noreply@academicpusher.com",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            if text_content:
                data["text"] = text_content

            try:
                response = requests.post(url, json=data, headers=headers, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Failed to send email via Resend to {to_email}: {e}")
                return False

        return True

    def _send_via_smtp(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send email via SMTP.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback content

        Returns:
            True if sent successfully
        """
        server = None
        try:
            # Create message once for all recipients (BCC style)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email or "noreply@academicpusher.com"
            # Set To to the first recipient (or all if sending to multiple at once)
            msg["To"] = ", ".join(to_emails) if len(to_emails) > 1 else to_emails[0]

            # Add plain text version
            if text_content:
                part_text = MIMEText(text_content, "plain", "utf-8")
                msg.attach(part_text)

            # Add HTML version
            part_html = MIMEText(html_content, "html", "utf-8")
            msg.attach(part_html)

            # Connect to SMTP server
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.ehlo()
                server.starttls()
                server.ehlo()

            # Login
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            # Send message once to all recipients
            server.send_message(msg)

            # Close connection
            server.quit()
            return True

        except Exception as e:
            if server:
                try:
                    server.quit()
                except:
                    pass
            raise RuntimeError(f"SMTP error: {type(e).__name__}: {e}") from e

    def send_report(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> dict:
        """Send report with detailed result.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback content

        Returns:
            Dictionary with send results for each email
        """
        results = {
            "success": [],
            "failed": [],
        }

        if self.use_resend:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {self.resend_api_key}",
                "Content-Type": "application/json",
            }

            for to_email in to_emails:
                data = {
                    "from": self.from_email or "noreply@academicpusher.com",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                }

                if text_content:
                    data["text"] = text_content

                try:
                    response = requests.post(url, json=data, headers=headers, timeout=30)
                    response.raise_for_status()
                    results["success"].append(to_email)
                except requests.RequestException as e:
                    results["failed"].append({"email": to_email, "error": str(e)})
        else:
            server = None
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.from_email or "noreply@academicpusher.com"
                msg["To"] = ", ".join(to_emails) if len(to_emails) > 1 else to_emails[0]

                if text_content:
                    part_text = MIMEText(text_content, "plain", "utf-8")
                    msg.attach(part_text)

                part_html = MIMEText(html_content, "html", "utf-8")
                msg.attach(part_html)

                # Connect to SMTP server
                if self.smtp_port == 465:
                    server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
                else:
                    server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                    server.ehlo()
                    server.starttls()
                    server.ehlo()

                # Login
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)

                # Send message once to all recipients
                server.send_message(msg)

                # All successful
                for to_email in to_emails:
                    results["success"].append(to_email)

                server.quit()

            except Exception as e:
                if server:
                    try:
                        server.quit()
                    except:
                        pass
                # Assume all failed if exception occurred
                error_msg = f"{type(e).__name__}: {e}"
                results["failed"] = [{"email": email, "error": error_msg} for email in to_emails]

        return results


def create_email_pusher(
    use_resend: bool = False,
    **kwargs,
) -> EmailPusher:
    """Factory function to create email pusher.

    Args:
        use_resend: Use Resend API instead of SMTP
        **kwargs: Additional arguments for EmailPusher

    Returns:
        Configured EmailPusher instance
    """
    return EmailPusher(use_resend=use_resend, **kwargs)
