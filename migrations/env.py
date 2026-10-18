from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from skriptoteket.infrastructure.db.base import Base
from skriptoteket.infrastructure.db.models.allowed_domain import AllowedDomainModel
from skriptoteket.infrastructure.db.models.blocked_domain import BlockedDomainModel
from skriptoteket.infrastructure.db.models.category import CategoryModel
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster import (
    RosterModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_share_artifact import (
    ClassroomPlannerShareArtifactModel,
    ClassroomPlannerSharePreviewAssetModel,
)
from skriptoteket.infrastructure.db.models.draft_lock import DraftLockModel
from skriptoteket.infrastructure.db.models.email_verification_token import (
    EmailVerificationTokenModel,
)
from skriptoteket.infrastructure.db.models.identity_projection import (
    IdentityProjectionEventModel,
    IdentityProjectionModel,
)
from skriptoteket.infrastructure.db.models.login_event import LoginEventModel
from skriptoteket.infrastructure.db.models.profession import ProfessionModel
from skriptoteket.infrastructure.db.models.profession_category import (
    ProfessionCategoryModel,
)
from skriptoteket.infrastructure.db.models.sandbox_snapshot import (
    SandboxSnapshotModel,
)
from skriptoteket.infrastructure.db.models.script_suggestion import (
    ScriptSuggestionModel,
)
from skriptoteket.infrastructure.db.models.script_suggestion_decision import (
    ScriptSuggestionDecisionModel,
)
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_category import ToolCategoryModel
from skriptoteket.infrastructure.db.models.tool_maintainer import (
    ToolMaintainerModel,
)
from skriptoteket.infrastructure.db.models.tool_maintainer_audit_log import (
    ToolMaintainerAuditLogModel,
)
from skriptoteket.infrastructure.db.models.tool_profession import ToolProfessionModel
from skriptoteket.infrastructure.db.models.tool_run import ToolRunModel
from skriptoteket.infrastructure.db.models.tool_run_job import ToolRunJobModel
from skriptoteket.infrastructure.db.models.tool_session import ToolSessionModel
from skriptoteket.infrastructure.db.models.tool_session_message import (
    ToolSessionMessageModel,
)
from skriptoteket.infrastructure.db.models.tool_session_turn import (
    ToolSessionTurnModel,
)
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.models.user_favorite import (
    UserFavoriteAppModel,
    UserFavoriteToolModel,
)
from skriptoteket.infrastructure.db.models.user_profile import UserProfileModel
from skriptoteket.infrastructure.db.models.user_vault_file import (
    UserVaultFileModel,
)
from skriptoteket.infrastructure.db.models.user_vault_usage import (
    UserVaultUsageModel,
)

# Explicitly use models to satisfy linter and ensure they are registered on Base.metadata
_MODELS = [
    AllowedDomainModel,
    BlockedDomainModel,
    CategoryModel,
    ClassroomPlannerShareArtifactModel,
    ClassroomPlannerSharePreviewAssetModel,
    RoomTemplateModel,
    RosterModel,
    DraftLockModel,
    EmailVerificationTokenModel,
    IdentityProjectionEventModel,
    IdentityProjectionModel,
    LoginEventModel,
    ProfessionModel,
    ProfessionCategoryModel,
    SandboxSnapshotModel,
    ScriptSuggestionModel,
    ScriptSuggestionDecisionModel,
    ToolModel,
    ToolCategoryModel,
    ToolMaintainerModel,
    ToolMaintainerAuditLogModel,
    ToolProfessionModel,
    ToolRunModel,
    ToolRunJobModel,
    ToolSessionModel,
    ToolSessionMessageModel,
    ToolSessionTurnModel,
    ToolVersionModel,
    UserModel,
    UserFavoriteAppModel,
    UserFavoriteToolModel,
    UserProfileModel,
    UserVaultFileModel,
    UserVaultUsageModel,
]

config = context.config

load_dotenv()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise ValueError("DATABASE_URL is not set")
    return url


def run_migrations_offline() -> None:
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
