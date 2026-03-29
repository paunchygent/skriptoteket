from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.identity.domain_allowlist_import import (
    DomainAllowlistImporter,
)
from skriptoteket.application.identity.domain_validator import TldextractDomainValidator
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import (
    AllowedDomain,
    OrganizationType,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    AllowedDomainRepositoryProtocol,
    BlockedDomainRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _build_validator() -> TldextractDomainValidator:
    return TldextractDomainValidator(
        allowed_domains=AsyncMock(spec=AllowedDomainRepositoryProtocol),
        blocked_domains=AsyncMock(spec=BlockedDomainRepositoryProtocol),
    )


def test_domain_validator_normalizes_email_subdomains() -> None:
    validator = _build_validator()

    assert validator.extract_root_domain_from_email("Teacher@Mail.Harryda.Se") == "harryda.se"


def test_domain_validator_rejects_subdomains_in_seed_rows() -> None:
    validator = _build_validator()

    with pytest.raises(DomainError) as exc_info:
        validator.normalize_seed_domain("mail.harryda.se")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_importer_dry_run_classifies_allowed_and_blocked_rows(
    tmp_path: Path, now: datetime
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

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    allowed_domains = AsyncMock(spec=AllowedDomainRepositoryProtocol)
    allowed_domains.get_by_domain.side_effect = [
        None,
        AllowedDomain(
            domain="vittra.se",
            org_type=OrganizationType.ENSKILD_HUVUDMAN,
            org_name="Vittra AB",
            source="skolverket_organizer_api",
            source_ref="https://api.skolverket.se/skolenhetsregistret/v2/organizers/5564586716",
            is_active=True,
            notes=None,
            created_at=now,
            updated_at=now,
        ),
    ]
    blocked_domains = AsyncMock(spec=BlockedDomainRepositoryProtocol)
    blocked_domains.get_by_domain.return_value = None

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    importer = DomainAllowlistImporter(
        uow=uow,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
        domain_validator=TldextractDomainValidator(
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
        ),
        clock=clock,
    )

    run = await importer.run(
        allowed_files=(municipalities_csv, enskilda_csv),
        blocked_files=(blocked_csv,),
        dry_run=True,
    )

    assert run.allowed.inserted == 1
    assert run.allowed.unchanged == 1
    assert run.allowed.updated == 0
    assert run.allowed.rejected == 0
    assert run.blocked.inserted == 1
    assert run.blocked.rejected == 0
    allowed_domains.upsert.assert_not_awaited()
    blocked_domains.upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_importer_rejects_duplicate_and_subdomain_rows(tmp_path: Path, now: datetime) -> None:
    municipalities_csv = tmp_path / "allowed_domains_municipalities.csv"
    enskilda_csv = tmp_path / "allowed_domains_enskilda_huvudman.csv"
    blocked_csv = tmp_path / "blocked_domains.csv"

    _write(
        municipalities_csv,
        (
            "domain,org_type,org_name,source,source_ref,is_active,notes\n"
            "harryda.se,kommun,Härryda kommun,skr_kommunlista,https://www.harryda.se/,true,\n"
            "mail.harryda.se,kommun,Härryda kommun,skr_kommunlista,https://www.harryda.se/,true,\n"
        ),
    )
    _write(
        enskilda_csv,
        (
            "domain,org_type,org_name,source,source_ref,is_active,notes\n"
            "harryda.se,enskild_huvudman,Duplicate AB,manual_seed,,true,\n"
        ),
    )
    _write(
        blocked_csv,
        "domain,reason,source,source_ref,is_active,notes\n",
    )

    importer = DomainAllowlistImporter(
        uow=AsyncMock(spec=UnitOfWorkProtocol),
        allowed_domains=AsyncMock(spec=AllowedDomainRepositoryProtocol),
        blocked_domains=AsyncMock(spec=BlockedDomainRepositoryProtocol),
        domain_validator=TldextractDomainValidator(
            allowed_domains=AsyncMock(spec=AllowedDomainRepositoryProtocol),
            blocked_domains=AsyncMock(spec=BlockedDomainRepositoryProtocol),
        ),
        clock=Mock(spec=ClockProtocol, now=Mock(return_value=now)),
    )

    run = await importer.run(
        allowed_files=(municipalities_csv, enskilda_csv),
        blocked_files=(blocked_csv,),
        dry_run=True,
    )

    assert run.allowed.rejected == 2
    assert run.allowed.inserted == 0
    assert run.allowed.updated == 0
    assert run.allowed.unchanged == 0
