from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.db.models.user import UserModel


async def create_user(*, db_session: AsyncSession, now: datetime) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"sandbox-{user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return user_id


async def create_tool(
    *,
    db_session: AsyncSession,
    now: datetime,
    owner_user_id: uuid.UUID,
) -> uuid.UUID:
    tool_id = uuid.uuid4()
    db_session.add(
        ToolModel(
            id=tool_id,
            owner_user_id=owner_user_id,
            slug=f"sandbox-tool-{tool_id.hex[:8]}",
            title="Sandbox tool",
            summary=None,
            is_published=False,
            active_version_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return tool_id


async def create_tool_version(
    *,
    db_session: AsyncSession,
    tool_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    now: datetime,
) -> uuid.UUID:
    version_id = uuid.uuid4()
    db_session.add(
        ToolVersionModel(
            id=version_id,
            tool_id=tool_id,
            version_number=1,
            state=VersionState.DRAFT,
            source_code="print('sandbox')",
            entrypoint="run_tool",
            content_hash="hash",
            derived_from_version_id=None,
            created_by_user_id=created_by_user_id,
            created_at=now,
            submitted_for_review_by_user_id=None,
            submitted_for_review_at=None,
            reviewed_by_user_id=None,
            reviewed_at=None,
            published_by_user_id=None,
            published_at=None,
            change_summary=None,
            review_note=None,
        )
    )
    await db_session.flush()
    return version_id
