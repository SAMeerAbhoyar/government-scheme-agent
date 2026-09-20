import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """
    SMTP Email stub.
    If SEND_EMAIL_NOTIFICATIONS is False, logs the email instead of sending.
    """
    if not settings.SEND_EMAIL_NOTIFICATIONS:
        logger.info(f"[EMAIL STUB - SEND_EMAIL_NOTIFICATIONS=False] To: {to_email} | Subject: {subject} | Body: {body}")
        return False
    
    try:
        # SMTP logic stub for when flag is enabled
        logger.info(f"[EMAIL SENT] To: {to_email} | Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
