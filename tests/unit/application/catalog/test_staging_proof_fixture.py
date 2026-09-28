"""Unit tests for the repeatable Hemma staging proof fixture.

Purpose:
    Prove that the fixture creates the contributor-maintained staging tool and
    draft once, is a no-op on a repeat run, and stops without writes when the
    fixture slug or draft belongs to someone else.

    Prove that the `setup-staging-proof-fixture` command refuses every target
    except the Hemma staging database before it opens a session.

Relationships:
    - Exercises `skriptoteket.application.catalog.staging_proof_fixture`.
    - Invokes `cli/commands/setup_staging_proof_fixture.py` through the
      registered Typer app.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from skriptoteket.application.catalog.staging_proof_fixture import (
    STAGING_PROOF_TOOL_SLUG,
    StagingProofFixture,
)
from skriptoteket.application.identity.huleedu_subject_export_contract import (
    parse_huleedu_subject_export,
)
from skriptoteket.cli.commands import setup_staging_proof_fixture
from skriptoteket.cli.main import app
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, UserAuth
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
ADMIN_EMAIL = "proof-admin@example.com"
CONTRIBUTOR_EMAIL = "proof-contributor@example.com"


class FakeUnitOfWork:
    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


def _export_payload() -> dict[str, object]:
    def account(key: str, email: str, role: str) -> dict[str, object]:
        return {
            "stable_account_key": key,
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "realm_subject_id": f"subject-{key}",
            "email": email,
            "email_verified": True,
            "skriptoteket_role_hint": role,
        }

    return {
        "status": "ok",
        "errors": [],
        "export": {
            "schema_version": "skriptoteket-proof-subject-export-v1",
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "accounts": [
                account("skriptoteket-proof-user", "proof-user@example.com", "user"),
                account("skriptoteket-proof-contributor", CONTRIBUTOR_EMAIL, "contributor"),
                account("skriptoteket-proof-admin", ADMIN_EMAIL, "admin"),
            ],
        },
    }


def _export():
    return parse_huleedu_subject_export(_export_payload())


def _build(*, contributor_role: Role = Role.CONTRIBUTOR):
    admin = make_user(role=Role.ADMIN, email=ADMIN_EMAIL)
    contributor = make_user(role=contributor_role, email=CONTRIBUTOR_EMAIL)
    auth_by_email = {
        ADMIN_EMAIL: UserAuth(user=admin),
        CONTRIBUTOR_EMAIL: UserAuth(user=contributor),
    }
    users = AsyncMock()
    users.get_auth_by_email.side_effect = lambda email: auth_by_email.get(email)

    draft_tool = make_tool(slug="draft-abc", owner_user_id=admin.id, now=NOW)
    renamed_tool = make_tool(
        slug=STAGING_PROOF_TOOL_SLUG, owner_user_id=admin.id, now=NOW, tool_id=draft_tool.id
    )
    draft_version = SimpleNamespace(id=uuid4(), created_by_user_id=contributor.id)

    deps = SimpleNamespace(
        tools=AsyncMock(),
        maintainers=AsyncMock(),
        versions=AsyncMock(),
        create_draft_tool=AsyncMock(),
        update_tool_slug=AsyncMock(),
        assign_maintainer=AsyncMock(),
        create_draft_version=AsyncMock(),
    )
    deps.tools.get_by_slug.return_value = None
    deps.maintainers.is_maintainer.return_value = False
    deps.versions.list_for_tool.return_value = []
    deps.create_draft_tool.handle.return_value = SimpleNamespace(tool=draft_tool)
    deps.update_tool_slug.handle.return_value = SimpleNamespace(tool=renamed_tool)
    deps.create_draft_version.handle.return_value = SimpleNamespace(version=draft_version)

    fixture = StagingProofFixture(uow=FakeUnitOfWork(), users=users, **vars(deps))
    return fixture, deps, admin, contributor, renamed_tool, draft_version


async def test_first_run_creates_tool_assigns_contributor_and_creates_contributor_draft() -> None:
    fixture, deps, admin, contributor, tool, draft = _build()

    result = await fixture.ensure(export=_export())

    assert deps.create_draft_tool.handle.await_args.kwargs["actor"] == admin
    slug_command = deps.update_tool_slug.handle.await_args.kwargs["command"]
    assert slug_command.slug == STAGING_PROOF_TOOL_SLUG
    assign = deps.assign_maintainer.handle.await_args.kwargs
    assert assign["actor"] == admin
    assert assign["command"].user_id == contributor.id
    draft_call = deps.create_draft_version.handle.await_args.kwargs
    assert draft_call["actor"] == contributor
    assert draft_call["command"].tool_id == tool.id
    assert "def run_tool(" in draft_call["command"].source_code
    assert result.tool_slug == STAGING_PROOF_TOOL_SLUG
    assert result.draft_version_id == draft.id
    assert (result.created_tool, result.assigned_maintainer, result.created_draft) == (
        True,
        True,
        True,
    )


async def test_repeat_run_reuses_existing_tool_maintainer_and_contributor_draft() -> None:
    fixture, deps, _admin, contributor, tool, draft = _build()
    deps.tools.get_by_slug.return_value = tool
    deps.maintainers.is_maintainer.return_value = True
    deps.versions.list_for_tool.return_value = [draft]

    result = await fixture.ensure(export=_export())

    deps.create_draft_tool.handle.assert_not_awaited()
    deps.update_tool_slug.handle.assert_not_awaited()
    deps.assign_maintainer.handle.assert_not_awaited()
    deps.create_draft_version.handle.assert_not_awaited()
    assert result.draft_version_id == draft.id
    assert (result.created_tool, result.assigned_maintainer, result.created_draft) == (
        False,
        False,
        False,
    )


async def test_existing_slug_tool_owned_by_someone_else_is_left_untouched() -> None:
    fixture, deps, *_ = _build()
    deps.tools.get_by_slug.return_value = make_tool(slug=STAGING_PROOF_TOOL_SLUG, now=NOW)

    with pytest.raises(DomainError) as exc_info:
        await fixture.ensure(export=_export())

    assert exc_info.value.code is ErrorCode.CONFLICT
    deps.maintainers.is_maintainer.assert_not_awaited()
    deps.assign_maintainer.handle.assert_not_awaited()
    deps.versions.list_for_tool.assert_not_awaited()
    deps.create_draft_version.handle.assert_not_awaited()


async def test_existing_draft_by_another_user_fails_closed() -> None:
    fixture, deps, _admin, _contributor, tool, _draft = _build()
    deps.tools.get_by_slug.return_value = tool
    deps.maintainers.is_maintainer.return_value = True
    deps.versions.list_for_tool.return_value = [
        SimpleNamespace(id=uuid4(), created_by_user_id=uuid4())
    ]

    with pytest.raises(DomainError) as exc_info:
        await fixture.ensure(export=_export())

    assert exc_info.value.code is ErrorCode.CONFLICT
    deps.create_draft_version.handle.assert_not_awaited()


async def test_contributor_without_mapped_role_fails_before_any_write() -> None:
    fixture, deps, *_ = _build(contributor_role=Role.USER)

    with pytest.raises(DomainError) as exc_info:
        await fixture.ensure(export=_export())

    assert exc_info.value.details["stable_account_key"] == "skriptoteket-proof-contributor"
    deps.create_draft_tool.handle.assert_not_awaited()


class SessionReached(Exception):
    """Raised by the test double once the command opens a database session."""


def _invoke_cli(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, environment: str, database_url: str
):
    opened: list[str] = []

    @asynccontextmanager
    async def open_session(settings):
        opened.append(settings.DATABASE_URL)
        raise SessionReached
        yield

    monkeypatch.setattr(setup_staging_proof_fixture, "open_session", open_session)
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("DATABASE_URL", database_url)
    export_path = tmp_path / "subject-export.json"
    export_path.write_text(json.dumps(_export_payload()), encoding="utf-8")

    result = CliRunner().invoke(
        app, ["setup-staging-proof-fixture", "--export-json", str(export_path)]
    )
    return result, opened


@pytest.mark.parametrize(
    ("environment", "database_url"),
    [
        (
            "production",
            "postgresql+asyncpg://skriptoteket:secret@shared-postgres:5432/skriptoteket",
        ),
        ("staging", "postgresql+asyncpg://skriptoteket:secret@shared-postgres:5432/skriptoteket"),
        ("production", "postgresql+asyncpg://skriptoteket:secret@db:5432/skriptoteket"),
        ("development", "postgresql+asyncpg://postgres:postgres@localhost:55432/skriptoteket"),
    ],
)
def test_cli_refuses_non_staging_targets_before_opening_a_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, environment: str, database_url: str
) -> None:
    result, opened = _invoke_cli(
        monkeypatch, tmp_path, environment=environment, database_url=database_url
    )

    assert result.exit_code == 1
    assert opened == []
    assert "Hemma staging database" in result.output
    assert "secret" not in result.output


def test_cli_opens_the_staging_database_for_the_staging_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result, opened = _invoke_cli(
        monkeypatch,
        tmp_path,
        environment="staging",
        database_url="postgresql+asyncpg://skriptoteket:secret@db:5432/skriptoteket",
    )

    assert isinstance(result.exception, SessionReached)
    assert len(opened) == 1
