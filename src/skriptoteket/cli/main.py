from __future__ import annotations

import typer

from skriptoteket.cli.commands.bootstrap_superuser import bootstrap_superuser
from skriptoteket.cli.commands.cleanup_login_events import cleanup_login_events
from skriptoteket.cli.commands.cleanup_sandbox_snapshots import cleanup_sandbox_snapshots
from skriptoteket.cli.commands.cleanup_session_files import cleanup_session_files
from skriptoteket.cli.commands.clear_all_session_files import clear_all_session_files
from skriptoteket.cli.commands.provision_user import provision_user
from skriptoteket.cli.commands.prune_artifacts import prune_artifacts
from skriptoteket.cli.commands.run_execution_worker import run_execution_worker
from skriptoteket.cli.commands.seed_script_bank import seed_script_bank

app = typer.Typer(no_args_is_help=True)

app.command()(bootstrap_superuser)
app.command()(provision_user)
app.command()(prune_artifacts)
app.command()(cleanup_session_files)
app.command()(cleanup_sandbox_snapshots)
app.command()(cleanup_login_events)
app.command()(clear_all_session_files)
app.command()(seed_script_bank)
app.command()(run_execution_worker)
