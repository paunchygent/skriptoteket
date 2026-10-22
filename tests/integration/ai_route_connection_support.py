"""Harness that counts held database connections while an AI provider call runs.

TASK-SKRIPT-41-01-04 unit E. Production's shared Postgres allows few connections, so a route
that keeps one checked out while its provider call runs caps the number of concurrent AI
calls. This harness serves the real web routes, the real signed-identity dependency, the
production container (``build_providers``) and a real PostgreSQL database; only the provider
seam is a fake. Each fake provider samples the connection count the moment it is called.

Two counts are sampled:

- ``checked_out``: connections the application engine's pool has handed out.
- ``idle_in_transaction``: server-side sessions of this database that sit in an open
  transaction. This also sees the unpooled connection of a payload guard.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import AsyncContainer, Provider, make_async_container
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.di import build_providers
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.projections import IdentityProjection, ProductIdentityRealm
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_maintainer import ToolMaintainerModel
from skriptoteket.infrastructure.repositories.identity_projection_repository import (
    PostgreSQLIdentityProjectionRepository,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as exam_api
from skriptoteket.web.api.v1.editor import router as editor_router
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    CONTEXT_SUBJECT,
    signed_huleedu_headers,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner

_IDLE_IN_TRANSACTION = text(
    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
    "AND pid <> pg_backend_pid() AND state LIKE 'idle in transaction%'"
)


@dataclass(frozen=True, slots=True)
class Sample:
    label: str
    checked_out: int
    idle_in_transaction: int

    @property
    def held(self) -> int:
        return max(self.checked_out, self.idle_in_transaction)


@dataclass(slots=True)
class ConnectionProbe:
    """Records the connections held at each moment a fake provider is called.

    The fake providers are registered in the container before its engine exists, so the
    harness binds the application engine and an unpooled observer engine afterwards.
    """

    samples: list[Sample] = field(default_factory=list)
    engine: AsyncEngine | None = None
    observer: AsyncEngine | None = None

    def bind(self, *, engine: AsyncEngine, observer: AsyncEngine) -> None:
        self.engine = engine
        self.observer = observer

    async def sample(self, label: str) -> None:
        assert self.engine is not None and self.observer is not None
        pool = self.engine.pool
        assert isinstance(pool, QueuePool)
        checked_out = pool.checkedout()
        async with self.observer.connect() as connection:
            idle = (await connection.execute(_IDLE_IN_TRANSACTION)).scalar_one()
        self.samples.append(Sample(label, checked_out, int(idle)))

    def held_during_calls(self) -> list[int]:
        return [sample.held for sample in self.samples]


@dataclass(frozen=True, slots=True)
class AiRouteHarness:
    client: httpx.AsyncClient
    container: AsyncContainer
    probe: ConnectionProbe
    actor: User
    headers: dict[str, str]
    tool_id: UUID


def _public_key_pem(private_key: rsa.RSAPrivateKey) -> str:
    return (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )


@asynccontextmanager
async def ai_route_harness(
    *,
    database_url: str,
    work_dir: Path,
    probe: ConnectionProbe,
    fakes: Provider,
) -> AsyncIterator[AiRouteHarness]:
    """Serve the editor and exam routes over the production container plus ``fakes``.

    ``fakes`` overrides the provider seams and samples ``probe`` when a provider is called.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings()
    settings.DATABASE_URL = database_url
    settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY = _public_key_pem(private_key)
    settings.LLM_COMPLETION_ENABLED = True
    settings.LLM_CHAT_ENABLED = True
    settings.LLM_CHAT_OPS_ENABLED = True
    settings.VAULT_ROOT = work_dir / "vault"
    settings.ARTIFACTS_ROOT = work_dir / "artifacts"
    container = make_async_container(*build_providers(settings), fakes)
    engine = await container.get(AsyncEngine)
    observer = create_async_engine(database_url, poolclass=NullPool)
    probe.bind(engine=engine, observer=observer)
    sessions = await container.get(async_sessionmaker[AsyncSession])

    actor = await create_owner(sessions, Role.CONTRIBUTOR)
    now = datetime.now(UTC)
    tool_id = uuid4()
    # A module's tests share one database, so each harness needs its own identity subject.
    subject = f"{CONTEXT_SUBJECT}-{uuid4().hex}"
    async with sessions() as session, session.begin():
        await PostgreSQLIdentityProjectionRepository(session).create_if_realm_subject_absent(
            projection=IdentityProjection(
                id=uuid4(),
                user_id=actor.id,
                product_identity_realm=ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
                realm_subject_id=subject,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ToolModel(
                id=tool_id,
                owner_user_id=actor.id,
                slug=f"ai-route-{tool_id.hex[:8]}",
                title="AI route tool",
                summary="Connection probe",
                created_at=now,
                updated_at=now,
            )
        )
        # The harness runs the editor routes as a contributor, which passes
        # `require_tool_access` only as a recorded maintainer; the owner row
        # alone does not satisfy the maintainer read.
        session.add(ToolMaintainerModel(tool_id=tool_id, user_id=actor.id))
    headers = signed_huleedu_headers(
        private_key=private_key, clock=FixedClock(now), subject=subject
    )

    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(editor_router)
    app.include_router(exam_api.router)
    setup_dishka(container, app)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield AiRouteHarness(
                client=client,
                container=container,
                probe=probe,
                actor=actor,
                headers=headers,
                tool_id=tool_id,
            )
    finally:
        await container.close()
        await engine.dispose()
        await observer.dispose()
