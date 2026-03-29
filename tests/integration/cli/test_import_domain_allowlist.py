from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.cli.commands.import_domain_allowlist import _run_domain_allowlist_import
from skriptoteket.infrastructure.repositories.allowed_domain_repository import (
    PostgreSQLAllowedDomainRepository,
)
from skriptoteket.infrastructure.repositories.blocked_domain_repository import (
    PostgreSQLBlockedDomainRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


@pytest.mark.integration
async def test_import_domain_allowlist_command_persists_seed_rows(
    tmp_path: Path,
    session_factory: async_sessionmaker[AsyncSession],
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    municipalities_csv = tmp_path / "allowed_domains_municipalities.csv"
    enskilda_csv = tmp_path / "allowed_domains_enskilda_huvudman.csv"
    blocked_csv = tmp_path / "blocked_domains.csv"

    _write(
        municipalities_csv,
        (
            "domain,org_type,org_name,source,source_ref,is_active,notes\n"
            "harryda.se,kommun,Härryda kommun,skr_kommunlista,https://www.harryda.se/,true,\n"
        ),
    )
    _write(
        enskilda_csv,
        (
            "domain,org_type,org_name,source,source_ref,is_active,notes\n"
            "vittra.se,enskild_huvudman,Vittra AB,skolverket_organizer_api,"
            "https://api.skolverket.se/skolenhetsregistret/v2/organizers/5564586716,true,\n"
        ),
    )
    _write(
        blocked_csv,
        (
            "domain,reason,source,source_ref,is_active,notes\n"
            "gmail.com,personal_email_provider,manual_seed,common_provider_seed,true,\n"
        ),
    )

    monkeypatch.setenv("DATABASE_URL", database_url)

    await _run_domain_allowlist_import(
        municipalities_csv=municipalities_csv,
        enskilda_csv=enskilda_csv,
        blocked_csv=blocked_csv,
        dry_run=False,
        validate_only=False,
    )

    async with session_factory() as session:
        allowed_repo = PostgreSQLAllowedDomainRepository(session)
        blocked_repo = PostgreSQLBlockedDomainRepository(session)

        assert (await allowed_repo.get_by_domain("harryda.se")) is not None
        assert (await allowed_repo.get_by_domain("vittra.se")) is not None
        blocked = await blocked_repo.get_by_domain("gmail.com")
        assert blocked is not None
        assert blocked.reason == "personal_email_provider"
