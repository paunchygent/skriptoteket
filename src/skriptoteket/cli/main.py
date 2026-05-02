"""Typer entrypoint for Skriptoteket operational and maintenance commands.

Purpose:
    Register CLI commands used by operators, workers, and docs-as-code
    verification scripts.

Relationships:
    - Command implementations live under `skriptoteket.cli.commands`.
    - Application services and repositories stay outside this composition file.
"""

from __future__ import annotations

import typer

from skriptoteket.cli.commands.backfill_classroom_share_previews import (
    backfill_classroom_share_previews,
)
from skriptoteket.cli.commands.bootstrap_superuser import bootstrap_superuser
from skriptoteket.cli.commands.cleanup_login_events import cleanup_login_events
from skriptoteket.cli.commands.cleanup_sandbox_snapshots import cleanup_sandbox_snapshots
from skriptoteket.cli.commands.cleanup_session_files import cleanup_session_files
from skriptoteket.cli.commands.cleanup_vault_files import cleanup_vault_files
from skriptoteket.cli.commands.clear_all_session_files import clear_all_session_files
from skriptoteket.cli.commands.consume_huleedu_subject_export import (
    consume_huleedu_subject_export,
)
from skriptoteket.cli.commands.healthcheck_execution_worker import healthcheck_execution_worker
from skriptoteket.cli.commands.import_domain_allowlist import (
    import_domain_allowlist,
    validate_domain_allowlist,
)
from skriptoteket.cli.commands.provision_user import provision_user
from skriptoteket.cli.commands.prune_artifacts import prune_artifacts
from skriptoteket.cli.commands.run_execution_worker import run_execution_worker
from skriptoteket.cli.commands.seed_script_bank import seed_script_bank
from skriptoteket.cli.commands.send_feedback_emails import send_feedback_emails
from skriptoteket.cli.commands.smoke_seating_export_readiness import (
    smoke_seating_export_readiness,
)

app = typer.Typer(no_args_is_help=True)

app.command()(backfill_classroom_share_previews)
app.command()(bootstrap_superuser)
app.command()(provision_user)
app.command()(consume_huleedu_subject_export)
app.command()(prune_artifacts)
app.command()(cleanup_session_files)
app.command()(cleanup_vault_files)
app.command()(cleanup_sandbox_snapshots)
app.command()(cleanup_login_events)
app.command()(clear_all_session_files)
app.command()(seed_script_bank)
app.command()(run_execution_worker)
app.command()(healthcheck_execution_worker)
app.command()(send_feedback_emails)
app.command()(smoke_seating_export_readiness)
app.command()(validate_domain_allowlist)
app.command()(import_domain_allowlist)
