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
from skriptoteket.infrastructure.db.models.category import CategoryModel  # noqa: F401
from skriptoteket.infrastructure.db.models.profession import ProfessionModel  # noqa: F401
from skriptoteket.infrastructure.db.models.profession_category import (  # noqa: F401
    ProfessionCategoryModel,
)
from skriptoteket.infrastructure.db.models.script_suggestion import (
    ScriptSuggestionModel,  # noqa: F401
)
from skriptoteket.infrastructure.db.models.script_suggestion_decision import (
    ScriptSuggestionDecisionModel,  # noqa: F401
)
from skriptoteket.infrastructure.db.models.session import SessionModel  # noqa: F401
from skriptoteket.infrastructure.db.models.tool import ToolModel  # noqa: F401
from skriptoteket.infrastructure.db.models.tool_category import ToolCategoryModel  # noqa: F401
from skriptoteket.infrastructure.db.models.tool_profession import ToolProfessionModel  # noqa: F401
from skriptoteket.infrastructure.db.models.user import UserModel  # noqa: F401

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
