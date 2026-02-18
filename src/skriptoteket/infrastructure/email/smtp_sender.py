"""SMTP email sender using aiosmtplib."""

from __future__ import annotations

import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from aiosmtplib import errors as smtp_errors

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.email import EmailMessage, EmailSenderProtocol

logger = logging.getLogger(__name__)

RETRYABLE_SMTP_CODES = frozenset(range(400, 500))


def _split_content_type(content_type: str) -> tuple[str, str]:
    if "/" not in content_type:
        return "application", "octet-stream"
    maintype, subtype = content_type.split("/", 1)
    cleaned_maintype = maintype.strip().lower() or "application"
    cleaned_subtype = subtype.strip().lower() or "octet-stream"
    return cleaned_maintype, cleaned_subtype


def _is_retryable_smtp_error(exc: smtp_errors.SMTPException) -> bool:
    if isinstance(
        exc,
        (
            smtp_errors.SMTPConnectError,
            smtp_errors.SMTPConnectTimeoutError,
            smtp_errors.SMTPReadTimeoutError,
            smtp_errors.SMTPTimeoutError,
            smtp_errors.SMTPServerDisconnected,
        ),
    ):
        return True

    if isinstance(
        exc,
        (
            smtp_errors.SMTPAuthenticationError,
            smtp_errors.SMTPRecipientRefused,
            smtp_errors.SMTPRecipientsRefused,
            smtp_errors.SMTPSenderRefused,
        ),
    ):
        return False

    if isinstance(exc, smtp_errors.SMTPResponseException):
        return exc.code in RETRYABLE_SMTP_CODES

    return False


class SmtpEmailSender(EmailSenderProtocol):
    """SMTP email sender using aiosmtplib."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, *, message: EmailMessage) -> None:
        """Send an email via SMTP."""
        if self._settings.EMAIL_PROVIDER == "mock":
            logger.info(
                "Email provider is mock, skipping email",
                extra={"to": message.to_email, "subject": message.subject},
            )
            return

        msg = MIMEMultipart("mixed" if message.attachments else "alternative")
        msg["Subject"] = message.subject
        msg["From"] = (
            f"{self._settings.EMAIL_DEFAULT_FROM_NAME} <{self._settings.EMAIL_DEFAULT_FROM_EMAIL}>"
        )
        msg["To"] = message.to_email

        text_part = MIMEText(message.text_body, "plain", "utf-8") if message.text_body else None
        html_part = MIMEText(message.html_body, "html", "utf-8")

        if message.attachments:
            body = MIMEMultipart("alternative")
            if text_part is not None:
                body.attach(text_part)
            body.attach(html_part)
            msg.attach(body)

            for attachment in message.attachments:
                maintype, subtype = _split_content_type(attachment.content_type)
                part = MIMEBase(maintype, subtype)
                part.set_payload(attachment.data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=attachment.filename)
                msg.attach(part)
        else:
            if text_part is not None:
                msg.attach(text_part)
            msg.attach(html_part)

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.EMAIL_SMTP_HOST,
                port=self._settings.EMAIL_SMTP_PORT,
                username=self._settings.EMAIL_SMTP_USERNAME,
                password=self._settings.EMAIL_SMTP_PASSWORD,
                start_tls=self._settings.EMAIL_SMTP_USE_TLS,
                timeout=self._settings.EMAIL_SMTP_TIMEOUT,
            )
            logger.info(
                "Email sent successfully",
                extra={"to": message.to_email, "subject": message.subject},
            )
        except aiosmtplib.SMTPException as e:
            is_retryable = _is_retryable_smtp_error(e)
            smtp_code = getattr(e, "code", None)
            logger.error(
                "Failed to send email",
                extra={
                    "to": message.to_email,
                    "error": str(e),
                    "retryable": is_retryable,
                    "smtp_code": smtp_code,
                    "smtp_error_type": type(e).__name__,
                },
            )
            raise DomainError(
                code=ErrorCode.EMAIL_SEND_FAILED,
                message="Kunde inte skicka e-post",
                details={
                    "retryable": is_retryable,
                    "smtp_code": smtp_code,
                    "smtp_error_type": type(e).__name__,
                },
            ) from e
