from __future__ import annotations

from pathlib import Path

import pytest

from skriptoteket.cli.commands.send_feedback_emails import (
    FeedbackManifestRow,
    _dispatch_feedback_emails,
    _extract_first_name,
    _load_manifest_rows,
    _render_template,
    _resolve_text_template,
    _wrap_text_body,
)
from skriptoteket.protocols.email import EmailMessage, EmailSenderProtocol


class CapturingEmailSender(EmailSenderProtocol):
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, *, message: EmailMessage) -> None:
        self.messages.append(message)


def test_load_manifest_rows_parses_required_columns(tmp_path: Path) -> None:
    manifest_csv = tmp_path / "manifest.csv"
    manifest_csv.write_text(
        (
            "student_id,name,email,pdf_filename,share_url,source_md\n"
            "1,Alice,alice@example.com,alice.pdf,,source-1.md\n"
            "2,Bob,bob@example.com,bob.pdf,https://example.com/source,source-2.md\n"
        ),
        encoding="utf-8",
    )

    rows = _load_manifest_rows(manifest_csv=manifest_csv)

    assert rows == [
        FeedbackManifestRow(
            student_id="1",
            name="Alice",
            email="alice@example.com",
            pdf_filename="alice.pdf",
            share_url=None,
            source_md="source-1.md",
        ),
        FeedbackManifestRow(
            student_id="2",
            name="Bob",
            email="bob@example.com",
            pdf_filename="bob.pdf",
            share_url="https://example.com/source",
            source_md="source-2.md",
        ),
    ]


def test_load_manifest_rows_requires_columns(tmp_path: Path) -> None:
    manifest_csv = tmp_path / "manifest.csv"
    manifest_csv.write_text(
        "student_id,name,email\n1,Alice,alice@example.com\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="missing required columns: pdf_filename"):
        _load_manifest_rows(manifest_csv=manifest_csv)


def test_extract_first_name() -> None:
    assert _extract_first_name("Ella Ytterstrom Silven") == "Ella"
    assert _extract_first_name("  Oskar   ") == "Oskar"


def test_render_template_supports_first_name() -> None:
    row = FeedbackManifestRow(
        student_id="1",
        name="Ella Ytterstrom Silven",
        email="ella@example.com",
        pdf_filename="ella.pdf",
        share_url=None,
        source_md=None,
    )

    rendered = _render_template(template="Hi {first_name}", row=row)

    assert rendered == "Hi Ella"


def test_resolve_text_template_from_file(tmp_path: Path) -> None:
    template_file = tmp_path / "template.txt"
    template_file.write_text("Hi {first_name}\n", encoding="utf-8")

    resolved = _resolve_text_template(
        inline_template="inline",
        template_file=template_file,
    )

    assert resolved == "Hi {first_name}\n"


def test_wrap_text_body_wraps_long_lines_to_width() -> None:
    wrapped = _wrap_text_body(
        text_body=(
            "This is a deliberately long sentence that should be wrapped to no more than twenty "
            "characters per line."
        ),
        wrap_width=20,
    )

    assert all(len(line) <= 20 for line in wrapped.splitlines() if line)


def test_wrap_text_body_disabled_when_width_zero() -> None:
    text = "A very long line that should stay untouched when wrapping is disabled."
    wrapped = _wrap_text_body(text_body=text, wrap_width=0)
    assert wrapped == text


@pytest.mark.asyncio
async def test_dispatch_feedback_emails_dry_run_prepares_rows(tmp_path: Path) -> None:
    (tmp_path / "alice.pdf").write_bytes(b"%PDF alice")
    sender = CapturingEmailSender()

    stats = await _dispatch_feedback_emails(
        rows=[
            FeedbackManifestRow(
                student_id="1",
                name="Alice",
                email="alice@example.com",
                pdf_filename="alice.pdf",
                share_url=None,
                source_md=None,
            )
        ],
        pdf_dir=tmp_path,
        subject_template="Feedback for {name}",
        text_template="Hi {name}",
        email_sender=sender,
        dry_run=True,
        test_recipient=None,
        pause_seconds=0,
        wrap_width=0,
        continue_on_error=False,
        show_rendered_text=False,
    )

    assert stats.total == 1
    assert stats.prepared == 1
    assert stats.sent == 0
    assert stats.failed == 0
    assert stats.skipped == 0
    assert sender.messages == []


@pytest.mark.asyncio
async def test_dispatch_feedback_emails_sends_with_attachment_and_override(tmp_path: Path) -> None:
    attachment_bytes = b"%PDF-1.7 mock"
    (tmp_path / "alice.pdf").write_bytes(attachment_bytes)
    sender = CapturingEmailSender()

    stats = await _dispatch_feedback_emails(
        rows=[
            FeedbackManifestRow(
                student_id="1",
                name="Alice",
                email="alice@example.com",
                pdf_filename="alice.pdf",
                share_url=None,
                source_md=None,
            )
        ],
        pdf_dir=tmp_path,
        subject_template="Feedback for {name}",
        text_template="Hi {name}",
        email_sender=sender,
        dry_run=False,
        test_recipient="teacher-test@example.com",
        pause_seconds=0,
        wrap_width=0,
        continue_on_error=False,
        show_rendered_text=False,
    )

    assert stats.total == 1
    assert stats.prepared == 1
    assert stats.sent == 1
    assert stats.failed == 0
    assert stats.skipped == 0

    assert len(sender.messages) == 1
    sent_message = sender.messages[0]
    assert sent_message.to_email == "teacher-test@example.com"
    assert sent_message.subject == "Feedback for Alice"
    assert sent_message.text_body == "Hi Alice"
    assert len(sent_message.attachments) == 1
    assert sent_message.attachments[0].filename == "alice.pdf"
    assert sent_message.attachments[0].data == attachment_bytes
    assert sent_message.attachments[0].content_type == "application/pdf"


@pytest.mark.asyncio
async def test_dispatch_feedback_emails_missing_pdf_stops_when_not_continuing(
    tmp_path: Path,
) -> None:
    sender = CapturingEmailSender()

    stats = await _dispatch_feedback_emails(
        rows=[
            FeedbackManifestRow(
                student_id="1",
                name="Alice",
                email="alice@example.com",
                pdf_filename="missing.pdf",
                share_url=None,
                source_md=None,
            ),
            FeedbackManifestRow(
                student_id="2",
                name="Bob",
                email="bob@example.com",
                pdf_filename="missing-2.pdf",
                share_url=None,
                source_md=None,
            ),
        ],
        pdf_dir=tmp_path,
        subject_template="Feedback for {name}",
        text_template="Hi {name}",
        email_sender=sender,
        dry_run=False,
        test_recipient=None,
        pause_seconds=0,
        wrap_width=0,
        continue_on_error=False,
        show_rendered_text=False,
    )

    assert stats.total == 2
    assert stats.prepared == 0
    assert stats.sent == 0
    assert stats.failed == 1
    assert stats.skipped == 2
    assert sender.messages == []
