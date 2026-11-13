---
type: runbook
id: RUN-SKRIPT-runbook-feedback-email-cli
title: 'Runbook: Feedback Email CLI'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
retired_ids:
- RUN-feedback-email-cli
summary: 'Runbook: Feedback Email CLI'
system: skriptoteket-email
---

## Trigger

Use this runbook to send student feedback emails with PDF attachments from a manifest CSV.

### When to use this runbook

- You have exported feedback PDFs and a manifest CSV with student/email/PDF mappings.
- You want a controlled send workflow with dry-run, test-recipient override, and row filters.
- You want to use `noreply@hule.education` via the configured email provider.

### Prerequisites

- SMTP (or mock) config is set in `.env`:
  - `EMAIL_PROVIDER`
  - `EMAIL_SMTP_HOST`
  - `EMAIL_SMTP_PORT`
  - `EMAIL_SMTP_USERNAME`
  - `EMAIL_SMTP_PASSWORD`
  - `EMAIL_DEFAULT_FROM_EMAIL`
- Manifest CSV includes columns:
  - `student_id`, `name`, `email`, `pdf_filename`
- PDF directory contains files named by each row's `pdf_filename`.

### Command

`pdm run send-feedback-emails`

Key options:

- `--manifest-csv <path>`
- `--pdf-dir <path>`
- `--dry-run/--send` (default is dry-run)
- `--text-template-file <path>` (load body template from a file)
- `--test-recipient <email>` (forces all sends to one address)
- `--only-student-id <id>` (repeatable)
- `--limit <n>`
- `--continue-on-error`
- `--pause-seconds <float>`
- `--wrap-width <n>` (default `0` = disabled)
- `--show-rendered-text` (print rendered subject/body for each selected row)

Template placeholders supported in subject/body:

- `{first_name}`
- `{name}`
- `{student_id}`
- `{email}`
- `{pdf_filename}`
- `{share_url}`
- `{source_md}`

### Iteration loop (recommended)

1. Create a local text template file (example `tmp/feedback-template.txt`).
2. Preview rendered output safely with dry-run:

```bash
pdm run send-feedback-emails \
  --manifest-csv "/path/to/export/manifest.csv" \
  --pdf-dir "/path/to/export/pdf" \
  --text-template-file "tmp/feedback-template.txt" \
  --dry-run \
  --show-rendered-text \
  --limit 2
```

3. Adjust wording and repeat until content looks right.
4. Run test send to your inbox only.
5. Run full student send.

### Safe rollout procedure

1. Dry-run a small subset:

```bash
pdm run send-feedback-emails \
  --manifest-csv "/path/to/export/manifest.csv" \
  --pdf-dir "/path/to/export/pdf" \
  --dry-run \
  --only-student-id 1 \
  --only-student-id 2
```

2. Send to a test inbox only (no student delivery yet):

```bash
pdm run send-feedback-emails \
  --manifest-csv "/path/to/export/manifest.csv" \
  --pdf-dir "/path/to/export/pdf" \
  --send \
  --test-recipient "teacher-test@example.com" \
  --limit 3
```

3. Send to all students:

```bash
pdm run send-feedback-emails \
  --manifest-csv "/path/to/export/manifest.csv" \
  --pdf-dir "/path/to/export/pdf" \
  --send
```

### Operational checks

- API/service readiness:
```bash
curl -s http://127.0.0.1:8000/healthz | jq '.status, .dependencies.smtp'
```
- SMTP troubleshooting:
  - See `docs/runbooks/runbook-observability-metrics.md` (`/healthz` SMTP section).
  - Review backend logs for `Failed to send email` and `EMAIL_SEND_FAILED`.

### Provider abstraction notes

- The CLI uses `EmailSenderProtocol` and the centralized sender factory:
  - `src/skriptoteket/infrastructure/email/sender_factory.py`
- To switch to a dedicated HuleEdu provider later, extend the sender factory and keep the CLI flow
  unchanged.

## Preconditions

The source material below remains authoritative for this section.

## Steps

The source material below remains authoritative for this section.

## Expected Results

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Rollback

The source boundaries and recovery limits remain preserved below.
