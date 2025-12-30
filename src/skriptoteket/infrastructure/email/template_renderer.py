"""Jinja2 email template renderer."""

from __future__ import annotations

import html as html_module
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from skriptoteket.protocols.email import EmailMessage, EmailTemplateRendererProtocol


class Jinja2EmailTemplateRenderer(EmailTemplateRendererProtocol):
    """Renders email templates using Jinja2."""

    SUBJECT_PATTERN = re.compile(r"<!--\s*subject:\s*(.+?)\s*-->", re.IGNORECASE)

    def __init__(self, templates_dir: Path | None = None) -> None:
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(
        self,
        *,
        template_name: str,
        context: dict[str, object],
    ) -> EmailMessage:
        """Render a template and extract subject from HTML comment."""
        template = self._env.get_template(template_name)
        html_body = template.render(**context)

        # Extract subject from HTML comment
        match = self.SUBJECT_PATTERN.search(html_body)
        if not match:
            raise ValueError(f"Template {template_name} missing subject comment")
        subject = match.group(1).strip()

        # Generate plain text from HTML
        text_body = self._html_to_text(html_body)

        # Validate to_email is provided
        to_email = context.get("to_email")
        if not to_email or not isinstance(to_email, str) or not to_email.strip():
            raise ValueError(f"Template {template_name} requires 'to_email' in context")

        return EmailMessage(
            to_email=to_email.strip(),
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to text conversion."""
        text = re.sub(r"<br\s*/?>", "\n", html)
        text = re.sub(r"</p>", "\n\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html_module.unescape(text)
        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines).strip()
