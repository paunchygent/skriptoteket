"""Email sender factory.

Centralizes provider selection so call-sites stay protocol-oriented.
"""

from __future__ import annotations

from skriptoteket.config import Settings
from skriptoteket.protocols.email import EmailSenderProtocol

from .smtp_sender import SmtpEmailSender


def create_email_sender(settings: Settings) -> EmailSenderProtocol:
    """Create configured email sender for the active provider."""
    if settings.EMAIL_PROVIDER in {"mock", "smtp"}:
        return SmtpEmailSender(settings)
    raise ValueError(f"Unsupported EMAIL_PROVIDER: {settings.EMAIL_PROVIDER}")
