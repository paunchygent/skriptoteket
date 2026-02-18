"""Email sending protocols."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class EmailAttachment(BaseModel):
    """Attachment payload for an email."""

    model_config = ConfigDict(frozen=True)

    filename: str
    data: bytes
    content_type: str = "application/octet-stream"


class EmailMessage(BaseModel):
    """Email message to be sent."""

    model_config = ConfigDict(frozen=True)

    to_email: str
    subject: str
    html_body: str
    text_body: str | None = None
    attachments: tuple[EmailAttachment, ...] = ()


class EmailSenderProtocol(Protocol):
    """Protocol for sending emails."""

    async def send(self, *, message: EmailMessage) -> None:
        """Send an email. Raises DomainError on failure."""
        ...


class EmailTemplateRendererProtocol(Protocol):
    """Protocol for rendering email templates."""

    def render(
        self,
        *,
        template_name: str,
        context: dict[str, object],
    ) -> EmailMessage:
        """Render a template and extract subject from HTML comment."""
        ...
