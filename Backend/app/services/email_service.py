"""
Async email delivery service.
Uses SMTP (aiosmtplib) when configured; logs to console in dev mode.
Configure via environment variables: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.
"""
from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


async def _send_email(to: str, subject: str, html_body: str, plain_body: str) -> bool:
    """
    Send an email via SMTP. Returns True on success, False on failure.
    Falls back to console logging if SMTP is not configured.
    """
    if not settings.SMTP_HOST:
        # Dev mode — log to console
        logger.info(
            "[EMAIL DEV] To: %s | Subject: %s\n%s",
            to, subject, plain_body,
        )
        return True

    try:
        import aiosmtplib  # type: ignore[import]

        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_TLS,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True

    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


async def send_password_reset_email(email: str, full_name: str, token: str) -> bool:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "PortFlow AI — Password Reset Request"
    plain = (
        f"Hello {full_name},\n\n"
        f"We received a request to reset your password.\n\n"
        f"Click the link below (valid for {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— PortFlow AI Security Team"
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a56db">PortFlow AI</h2>
      <p>Hello <strong>{full_name}</strong>,</p>
      <p>We received a request to reset your PortFlow AI password.</p>
      <p style="margin:24px 0">
        <a href="{reset_url}"
           style="background:#1a56db;color:#fff;padding:12px 24px;
                  border-radius:6px;text-decoration:none;font-weight:bold">
          Reset My Password
        </a>
      </p>
      <p>This link expires in <strong>{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes</strong>.</p>
      <p>If you did not request a password reset, you can safely ignore this email.</p>
      <hr/>
      <small style="color:#6b7280">PortFlow AI Security Team</small>
    </body></html>
    """
    return await _send_email(email, subject, html, plain)


async def send_notification_email(
    to: str,
    subject: str,
    body: str,
) -> bool:
    """Generic notification email — used by the notification service."""
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a56db">PortFlow AI</h2>
      <div style="white-space:pre-line">{body}</div>
      <hr/>
      <small style="color:#6b7280">PortFlow AI Notification System</small>
    </body></html>
    """
    return await _send_email(to, subject, html, body)


async def send_vessel_arrival_notification(
    to: str,
    vessel_name: str,
    imo: str,
    eta: str,
    berth_name: str | None,
) -> bool:
    subject = f"PortFlow AI — Vessel Arrival: {vessel_name}"
    plain = (
        f"Vessel {vessel_name} (IMO: {imo}) is expected to arrive at {eta}.\n"
        f"Assigned berth: {berth_name or 'TBD'}"
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a56db">PortFlow AI — Vessel Arrival Alert</h2>
      <table cellpadding="8" cellspacing="0" border="1" style="border-collapse:collapse;width:100%">
        <tr><td><strong>Vessel</strong></td><td>{vessel_name}</td></tr>
        <tr><td><strong>IMO</strong></td><td>{imo}</td></tr>
        <tr><td><strong>ETA</strong></td><td>{eta}</td></tr>
        <tr><td><strong>Berth</strong></td><td>{berth_name or "TBD"}</td></tr>
      </table>
      <hr/>
      <small style="color:#6b7280">PortFlow AI Notification System</small>
    </body></html>
    """
    return await _send_email(to, subject, html, plain)
