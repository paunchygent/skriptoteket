from __future__ import annotations

import asyncio
import csv
import html as html_module
import textwrap
from dataclasses import dataclass
from pathlib import Path

import typer

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.email.sender_factory import create_email_sender
from skriptoteket.protocols.email import EmailAttachment, EmailMessage, EmailSenderProtocol

DEFAULT_SUBJECT_TEMPLATE = "Your topic proposal feedback (research prompt)"
DEFAULT_TEXT_TEMPLATE = (
    "Hi {first_name},\n\n"
    "Olof here!\n\n"
    "I am trying out a new thing here. I ran all of your proposals through my "
    '"research prompt," which I like to use whenever I start a fresh research project. '
    "You can find the results from this query in the attached PDF.\n\n"
    "Best regards,\n"
    "Olof\n"
    "(HuleEdu is my domain)"
)
REQUIRED_MANIFEST_COLUMNS = frozenset({"student_id", "name", "email", "pdf_filename"})


@dataclass(frozen=True)
class FeedbackManifestRow:
    student_id: str
    name: str
    email: str
    pdf_filename: str
    share_url: str | None
    source_md: str | None


@dataclass(frozen=True)
class FeedbackDispatchStats:
    total: int
    prepared: int
    sent: int
    failed: int
    skipped: int


def send_feedback_emails(
    manifest_csv: Path = typer.Option(..., help="CSV file with student/email/pdf mapping."),
    pdf_dir: Path = typer.Option(..., help="Directory that contains feedback PDF files."),
    subject_template: str = typer.Option(DEFAULT_SUBJECT_TEMPLATE),
    text_template: str = typer.Option(DEFAULT_TEXT_TEMPLATE),
    text_template_file: Path | None = typer.Option(
        None,
        help="Optional file path for email text template (overrides --text-template).",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--send",
        help="Preview recipients/files without sending (default: dry-run).",
    ),
    only_student_id: list[str] | None = typer.Option(
        None,
        "--only-student-id",
        help="Send only for the listed student id(s). May be repeated.",
    ),
    limit: int | None = typer.Option(None, min=1, help="Max rows to process after filtering."),
    test_recipient: str | None = typer.Option(
        None,
        help="Override all recipient addresses (safe test mode).",
    ),
    pause_seconds: float = typer.Option(
        0.0,
        min=0.0,
        help="Pause between sends to reduce provider rate pressure.",
    ),
    wrap_width: int = typer.Option(
        0,
        min=0,
        help="Wrap rendered text body to this line width (0 disables hard wrapping).",
    ),
    continue_on_error: bool = typer.Option(
        False,
        help="Continue sending after row-level errors.",
    ),
    show_rendered_text: bool = typer.Option(
        False,
        help="Print rendered subject/text per row (best with --dry-run and --limit).",
    ),
) -> None:
    """Send manifest-driven feedback emails with PDF attachments."""
    asyncio.run(
        _send_feedback_emails_async(
            manifest_csv=manifest_csv,
            pdf_dir=pdf_dir,
            subject_template=subject_template,
            text_template=text_template,
            text_template_file=text_template_file,
            dry_run=dry_run,
            only_student_id=only_student_id or [],
            limit=limit,
            test_recipient=test_recipient,
            pause_seconds=pause_seconds,
            wrap_width=wrap_width,
            continue_on_error=continue_on_error,
            show_rendered_text=show_rendered_text,
        )
    )


async def _send_feedback_emails_async(
    *,
    manifest_csv: Path,
    pdf_dir: Path,
    subject_template: str,
    text_template: str,
    text_template_file: Path | None,
    dry_run: bool,
    only_student_id: list[str],
    limit: int | None,
    test_recipient: str | None,
    pause_seconds: float,
    wrap_width: int,
    continue_on_error: bool,
    show_rendered_text: bool,
) -> None:
    if not manifest_csv.exists():
        raise SystemExit(f"Manifest CSV not found: {manifest_csv}")
    if not manifest_csv.is_file():
        raise SystemExit(f"Manifest path must be a file: {manifest_csv}")
    if not pdf_dir.exists():
        raise SystemExit(f"PDF directory not found: {pdf_dir}")
    if not pdf_dir.is_dir():
        raise SystemExit(f"PDF path must be a directory: {pdf_dir}")

    rows = _load_manifest_rows(manifest_csv=manifest_csv)
    rows = _filter_rows(rows=rows, only_student_ids=only_student_id, limit=limit)
    if not rows:
        raise SystemExit("No rows selected after filtering.")
    effective_text_template = _resolve_text_template(
        inline_template=text_template,
        template_file=text_template_file,
    )

    settings = Settings()
    email_sender = create_email_sender(settings)
    stats = await _dispatch_feedback_emails(
        rows=rows,
        pdf_dir=pdf_dir,
        subject_template=subject_template,
        text_template=effective_text_template,
        email_sender=email_sender,
        dry_run=dry_run,
        test_recipient=test_recipient,
        pause_seconds=pause_seconds,
        wrap_width=wrap_width,
        continue_on_error=continue_on_error,
        show_rendered_text=show_rendered_text,
    )

    typer.echo(
        "Feedback email run complete: "
        f"total={stats.total} "
        f"prepared={stats.prepared} "
        f"sent={stats.sent} "
        f"failed={stats.failed} "
        f"skipped={stats.skipped} "
        f"mode={'dry-run' if dry_run else 'send'}"
    )
    if not dry_run and stats.failed > 0 and not continue_on_error:
        raise SystemExit("Run stopped after first error (use --continue-on-error to continue).")
    if not dry_run and stats.failed > 0:
        raise SystemExit("Run completed with one or more failed rows.")


def _load_manifest_rows(*, manifest_csv: Path) -> list[FeedbackManifestRow]:
    with manifest_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_MANIFEST_COLUMNS - fieldnames)
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise SystemExit(f"Manifest is missing required columns: {missing}")

        rows: list[FeedbackManifestRow] = []
        for line_number, row in enumerate(reader, start=2):
            if row is None:
                continue
            parsed = _parse_manifest_row(row=row, line_number=line_number)
            rows.append(parsed)
    return rows


def _parse_manifest_row(*, row: dict[str, str | None], line_number: int) -> FeedbackManifestRow:
    student_id = _required_manifest_value(row=row, key="student_id", line_number=line_number)
    name = _required_manifest_value(row=row, key="name", line_number=line_number)
    email = _required_manifest_value(row=row, key="email", line_number=line_number)
    pdf_filename = _required_manifest_value(row=row, key="pdf_filename", line_number=line_number)
    if "@" not in email:
        raise SystemExit(f"Invalid email at line {line_number}: {email}")

    return FeedbackManifestRow(
        student_id=student_id,
        name=name,
        email=email,
        pdf_filename=pdf_filename,
        share_url=_optional_manifest_value(row=row, key="share_url"),
        source_md=_optional_manifest_value(row=row, key="source_md"),
    )


def _required_manifest_value(*, row: dict[str, str | None], key: str, line_number: int) -> str:
    value = _optional_manifest_value(row=row, key=key)
    if value is None:
        raise SystemExit(f"Manifest column '{key}' is empty at line {line_number}")
    return value


def _optional_manifest_value(*, row: dict[str, str | None], key: str) -> str | None:
    raw = row.get(key)
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


def _filter_rows(
    *,
    rows: list[FeedbackManifestRow],
    only_student_ids: list[str],
    limit: int | None,
) -> list[FeedbackManifestRow]:
    filtered = rows
    if only_student_ids:
        selected_ids = {item.strip() for item in only_student_ids if item.strip()}
        filtered = [row for row in filtered if row.student_id in selected_ids]
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def _resolve_text_template(*, inline_template: str, template_file: Path | None) -> str:
    if template_file is None:
        return inline_template
    if not template_file.exists():
        raise SystemExit(f"Template file not found: {template_file}")
    if not template_file.is_file():
        raise SystemExit(f"Template path must be a file: {template_file}")
    loaded = template_file.read_text(encoding="utf-8")
    if not loaded.strip():
        raise SystemExit(f"Template file is empty: {template_file}")
    return loaded


def _extract_first_name(full_name: str) -> str:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return full_name.strip()
    return parts[0]


def _render_template(*, template: str, row: FeedbackManifestRow) -> str:
    try:
        first_name = _extract_first_name(row.name)
        return template.format(
            student_id=row.student_id,
            name=row.name,
            first_name=first_name,
            email=row.email,
            pdf_filename=row.pdf_filename,
            share_url=row.share_url or "",
            source_md=row.source_md or "",
        )
    except KeyError as exc:
        raise SystemExit(f"Unknown template placeholder: {exc.args[0]}") from exc


def _text_to_html_body(*, text_body: str) -> str:
    escaped_text = html_module.escape(text_body)
    return f"<html><body><p>{escaped_text.replace(chr(10), '<br>')}</p></body></html>"


def _wrap_text_body(*, text_body: str, wrap_width: int) -> str:
    if wrap_width <= 0:
        return text_body

    wrapped_lines: list[str] = []
    for line in text_body.splitlines():
        if not line.strip():
            wrapped_lines.append("")
            continue
        chunks = textwrap.wrap(
            line,
            width=wrap_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        wrapped_lines.extend(chunks if chunks else [""])
    return "\n".join(wrapped_lines)


async def _dispatch_feedback_emails(
    *,
    rows: list[FeedbackManifestRow],
    pdf_dir: Path,
    subject_template: str,
    text_template: str,
    email_sender: EmailSenderProtocol,
    dry_run: bool,
    test_recipient: str | None,
    pause_seconds: float,
    wrap_width: int,
    continue_on_error: bool,
    show_rendered_text: bool,
) -> FeedbackDispatchStats:
    prepared = 0
    sent = 0
    failed = 0
    skipped = 0

    target_override = test_recipient.strip() if test_recipient else None

    for row in rows:
        pdf_path = pdf_dir / row.pdf_filename
        if not pdf_path.is_file():
            failed += 1
            typer.echo(f"[ERROR] Missing PDF for student_id={row.student_id}: {pdf_path}")
            if not continue_on_error:
                break
            continue

        to_email = target_override or row.email
        subject = _render_template(template=subject_template, row=row)
        text_body = _render_template(template=text_template, row=row)
        text_body = _wrap_text_body(text_body=text_body, wrap_width=wrap_width)
        html_body = _text_to_html_body(text_body=text_body)
        if show_rendered_text:
            typer.echo(f"[PREVIEW] student_id={row.student_id} subject={subject}")
            typer.echo(text_body)
            typer.echo("[PREVIEW-END]")
        attachment = EmailAttachment(
            filename=row.pdf_filename,
            data=pdf_path.read_bytes(),
            content_type="application/pdf",
        )
        message = EmailMessage(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            attachments=(attachment,),
        )

        prepared += 1
        if dry_run:
            typer.echo(
                f"[DRY-RUN] student_id={row.student_id} to={to_email} attachment={row.pdf_filename}"
            )
            continue

        try:
            await email_sender.send(message=message)
            sent += 1
            typer.echo(f"[SENT] student_id={row.student_id} to={to_email}")
        except DomainError as exc:
            failed += 1
            typer.echo(
                f"[ERROR] student_id={row.student_id} to={to_email} code={exc.code.value} "
                f"message={exc.message}"
            )
            if not continue_on_error:
                break
        except Exception as exc:  # pragma: no cover
            failed += 1
            typer.echo(
                f"[ERROR] student_id={row.student_id} to={to_email} error_type={type(exc).__name__}"
            )
            if not continue_on_error:
                break

        if pause_seconds > 0:
            await asyncio.sleep(pause_seconds)

    skipped = len(rows) - prepared
    return FeedbackDispatchStats(
        total=len(rows),
        prepared=prepared,
        sent=sent,
        failed=failed,
        skipped=skipped,
    )
