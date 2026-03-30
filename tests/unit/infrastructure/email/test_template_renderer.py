"""Regression tests for email template rendering contracts.

Purpose:
  Prove the shipped auth email templates satisfy the shared renderer
  requirements and avoid the known broken verification-image regression.

Relationships:
  - Guards `src/skriptoteket/infrastructure/email/template_renderer.py`.
  - Exercises the production templates under
    `src/skriptoteket/infrastructure/email/templates/`.
"""

from skriptoteket.infrastructure.email.template_renderer import Jinja2EmailTemplateRenderer


def test_reset_password_template_includes_subject_comment() -> None:
    renderer = Jinja2EmailTemplateRenderer()

    message = renderer.render(
        template_name="reset_password.html",
        context={
            "to_email": "olof.larsson@harryda.se",
            "first_name": "Olof",
            "reset_url": "https://skriptoteket.hule.education/reset-password?token=test",
            "expiry_hours": 2,
        },
    )

    assert message.subject == "Återställ ditt lösenord - Skriptoteket"
    assert "https://skriptoteket.hule.education/reset-password?token=test" in message.html_body


def test_verify_email_template_has_no_remote_header_image() -> None:
    renderer = Jinja2EmailTemplateRenderer()

    message = renderer.render(
        template_name="verify_email.html",
        context={
            "to_email": "olof.larsson@harryda.se",
            "first_name": "Olof",
            "verification_url": "https://skriptoteket.hule.education/verify-email?token=test",
            "expiry_hours": 24,
            "base_url": "https://skriptoteket.hule.education",
        },
    )

    assert "logo-email.png" not in message.html_body
    assert "<img" not in message.html_body
