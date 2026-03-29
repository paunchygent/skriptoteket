"""CSV import service for registration allowlist and blocklist seed data.

Purpose:
  Validate the repo-managed CSV contract, normalize root domains, and upsert the
  current baseline into PostgreSQL in a deterministic, operator-friendly way.

Relationships:
  - Depends on the domain validator plus allowlist/blocklist repositories.
  - Used by CLI commands for dry-run validation and actual imports.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AllowedDomain, BlockedDomain, OrganizationType
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    AllowedDomainRepositoryProtocol,
    BlockedDomainRepositoryProtocol,
    DomainValidatorProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

ALLOWED_DOMAIN_HEADERS = (
    "domain",
    "org_type",
    "org_name",
    "source",
    "source_ref",
    "is_active",
    "notes",
)
BLOCKED_DOMAIN_HEADERS = (
    "domain",
    "reason",
    "source",
    "source_ref",
    "is_active",
    "notes",
)


@dataclass(frozen=True)
class RejectedImportRow:
    file_path: str
    line_number: int
    domain: str | None
    reason: str


@dataclass(frozen=True)
class ImportSummary:
    label: str
    total_rows: int
    inserted: int
    updated: int
    unchanged: int
    rejected_rows: tuple[RejectedImportRow, ...]
    dry_run: bool

    @property
    def rejected(self) -> int:
        return len(self.rejected_rows)

    @property
    def has_errors(self) -> bool:
        return self.rejected > 0


@dataclass(frozen=True)
class DomainAllowlistImportRun:
    allowed: ImportSummary
    blocked: ImportSummary

    @property
    def has_errors(self) -> bool:
        return self.allowed.has_errors or self.blocked.has_errors


@dataclass(frozen=True)
class _AllowedSeedRow:
    domain: str
    org_type: OrganizationType
    org_name: str
    source: str
    source_ref: str | None
    is_active: bool
    notes: str | None


@dataclass(frozen=True)
class _BlockedSeedRow:
    domain: str
    reason: str | None
    source: str
    source_ref: str | None
    is_active: bool
    notes: str | None


class DomainAllowlistImporter:
    """Validate CSV seed files and upsert them into the current database."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        allowed_domains: AllowedDomainRepositoryProtocol,
        blocked_domains: BlockedDomainRepositoryProtocol,
        domain_validator: DomainValidatorProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._allowed_domains = allowed_domains
        self._blocked_domains = blocked_domains
        self._domain_validator = domain_validator
        self._clock = clock

    async def run(
        self,
        *,
        allowed_files: tuple[Path, ...],
        blocked_files: tuple[Path, ...],
        dry_run: bool,
    ) -> DomainAllowlistImportRun:
        allowed_rows, allowed_rejections = self._load_allowed_rows(allowed_files)
        blocked_rows, blocked_rejections = self._load_blocked_rows(blocked_files)

        if allowed_rejections or blocked_rejections:
            return DomainAllowlistImportRun(
                allowed=self._rejection_summary(
                    label="allowed",
                    total_rows=len(allowed_rows) + len(allowed_rejections),
                    rejections=allowed_rejections,
                    dry_run=dry_run,
                ),
                blocked=self._rejection_summary(
                    label="blocked",
                    total_rows=len(blocked_rows) + len(blocked_rejections),
                    rejections=blocked_rejections,
                    dry_run=dry_run,
                ),
            )

        allowed_summary = await self._sync_allowed_rows(
            rows=allowed_rows,
            dry_run=dry_run,
        )
        blocked_summary = await self._sync_blocked_rows(
            rows=blocked_rows,
            dry_run=dry_run,
        )
        return DomainAllowlistImportRun(allowed=allowed_summary, blocked=blocked_summary)

    def _load_allowed_rows(
        self, file_paths: tuple[Path, ...]
    ) -> tuple[list[_AllowedSeedRow], list[RejectedImportRow]]:
        rows: list[_AllowedSeedRow] = []
        rejections: list[RejectedImportRow] = []
        seen_domains: dict[str, tuple[str, int]] = {}

        for file_path in file_paths:
            for line_number, raw_row in self._read_csv_rows(
                file_path=file_path,
                expected_headers=ALLOWED_DOMAIN_HEADERS,
                rejections=rejections,
            ):
                try:
                    normalized_domain = self._domain_validator.normalize_seed_domain(
                        self._required_value(
                            raw_row=raw_row,
                            key="domain",
                            file_path=file_path,
                            line_number=line_number,
                        )
                    )
                    if normalized_domain in seen_domains:
                        first_file, first_line = seen_domains[normalized_domain]
                        raise DomainError(
                            code=ErrorCode.VALIDATION_ERROR,
                            message=(
                                f"Duplicate domain in import run; first seen at "
                                f"{first_file}:{first_line}"
                            ),
                        )
                    seen_domains[normalized_domain] = (str(file_path), line_number)
                    rows.append(
                        _AllowedSeedRow(
                            domain=normalized_domain,
                            org_type=OrganizationType(
                                self._required_value(
                                    raw_row=raw_row,
                                    key="org_type",
                                    file_path=file_path,
                                    line_number=line_number,
                                )
                            ),
                            org_name=self._required_value(
                                raw_row=raw_row,
                                key="org_name",
                                file_path=file_path,
                                line_number=line_number,
                            ),
                            source=self._required_value(
                                raw_row=raw_row,
                                key="source",
                                file_path=file_path,
                                line_number=line_number,
                            ),
                            source_ref=self._optional_value(raw_row=raw_row, key="source_ref"),
                            is_active=self._parse_bool(
                                raw_value=self._required_value(
                                    raw_row=raw_row,
                                    key="is_active",
                                    file_path=file_path,
                                    line_number=line_number,
                                )
                            ),
                            notes=self._optional_value(raw_row=raw_row, key="notes"),
                        )
                    )
                except (DomainError, ValueError) as exc:
                    rejections.append(
                        RejectedImportRow(
                            file_path=str(file_path),
                            line_number=line_number,
                            domain=raw_row.get("domain"),
                            reason=str(exc),
                        )
                    )

        return rows, rejections

    def _load_blocked_rows(
        self, file_paths: tuple[Path, ...]
    ) -> tuple[list[_BlockedSeedRow], list[RejectedImportRow]]:
        rows: list[_BlockedSeedRow] = []
        rejections: list[RejectedImportRow] = []
        seen_domains: dict[str, tuple[str, int]] = {}

        for file_path in file_paths:
            for line_number, raw_row in self._read_csv_rows(
                file_path=file_path,
                expected_headers=BLOCKED_DOMAIN_HEADERS,
                rejections=rejections,
            ):
                try:
                    normalized_domain = self._domain_validator.normalize_seed_domain(
                        self._required_value(
                            raw_row=raw_row,
                            key="domain",
                            file_path=file_path,
                            line_number=line_number,
                        )
                    )
                    if normalized_domain in seen_domains:
                        first_file, first_line = seen_domains[normalized_domain]
                        raise DomainError(
                            code=ErrorCode.VALIDATION_ERROR,
                            message=(
                                f"Duplicate domain in import run; first seen at "
                                f"{first_file}:{first_line}"
                            ),
                        )
                    seen_domains[normalized_domain] = (str(file_path), line_number)
                    rows.append(
                        _BlockedSeedRow(
                            domain=normalized_domain,
                            reason=self._optional_value(raw_row=raw_row, key="reason"),
                            source=self._required_value(
                                raw_row=raw_row,
                                key="source",
                                file_path=file_path,
                                line_number=line_number,
                            ),
                            source_ref=self._optional_value(raw_row=raw_row, key="source_ref"),
                            is_active=self._parse_bool(
                                raw_value=self._required_value(
                                    raw_row=raw_row,
                                    key="is_active",
                                    file_path=file_path,
                                    line_number=line_number,
                                )
                            ),
                            notes=self._optional_value(raw_row=raw_row, key="notes"),
                        )
                    )
                except (DomainError, ValueError) as exc:
                    rejections.append(
                        RejectedImportRow(
                            file_path=str(file_path),
                            line_number=line_number,
                            domain=raw_row.get("domain"),
                            reason=str(exc),
                        )
                    )

        return rows, rejections

    async def _sync_allowed_rows(
        self,
        *,
        rows: list[_AllowedSeedRow],
        dry_run: bool,
    ) -> ImportSummary:
        inserted = 0
        updated = 0
        unchanged = 0
        now = self._clock.now()

        async def classify_and_write() -> None:
            nonlocal inserted, updated, unchanged
            for row in rows:
                existing = await self._allowed_domains.get_by_domain(row.domain)
                if existing is None:
                    inserted += 1
                    if not dry_run:
                        await self._allowed_domains.upsert(
                            domain=AllowedDomain(
                                domain=row.domain,
                                org_type=row.org_type,
                                org_name=row.org_name,
                                source=row.source,
                                source_ref=row.source_ref,
                                is_active=row.is_active,
                                notes=row.notes,
                                created_at=now,
                                updated_at=now,
                            )
                        )
                    continue

                if self._allowed_rows_equal(existing=existing, seed=row):
                    unchanged += 1
                    continue

                updated += 1
                if not dry_run:
                    await self._allowed_domains.upsert(
                        domain=AllowedDomain(
                            domain=row.domain,
                            org_type=row.org_type,
                            org_name=row.org_name,
                            source=row.source,
                            source_ref=row.source_ref,
                            is_active=row.is_active,
                            notes=row.notes,
                            created_at=existing.created_at,
                            updated_at=now,
                        )
                    )

        if dry_run:
            await classify_and_write()
        else:
            async with self._uow:
                await classify_and_write()

        return ImportSummary(
            label="allowed",
            total_rows=len(rows),
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            rejected_rows=(),
            dry_run=dry_run,
        )

    async def _sync_blocked_rows(
        self,
        *,
        rows: list[_BlockedSeedRow],
        dry_run: bool,
    ) -> ImportSummary:
        inserted = 0
        updated = 0
        unchanged = 0
        now = self._clock.now()

        async def classify_and_write() -> None:
            nonlocal inserted, updated, unchanged
            for row in rows:
                existing = await self._blocked_domains.get_by_domain(row.domain)
                if existing is None:
                    inserted += 1
                    if not dry_run:
                        await self._blocked_domains.upsert(
                            domain=BlockedDomain(
                                domain=row.domain,
                                reason=row.reason,
                                source=row.source,
                                source_ref=row.source_ref,
                                is_active=row.is_active,
                                notes=row.notes,
                                created_at=now,
                                updated_at=now,
                            )
                        )
                    continue

                if self._blocked_rows_equal(existing=existing, seed=row):
                    unchanged += 1
                    continue

                updated += 1
                if not dry_run:
                    await self._blocked_domains.upsert(
                        domain=BlockedDomain(
                            domain=row.domain,
                            reason=row.reason,
                            source=row.source,
                            source_ref=row.source_ref,
                            is_active=row.is_active,
                            notes=row.notes,
                            created_at=existing.created_at,
                            updated_at=now,
                        )
                    )

        if dry_run:
            await classify_and_write()
        else:
            async with self._uow:
                await classify_and_write()

        return ImportSummary(
            label="blocked",
            total_rows=len(rows),
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            rejected_rows=(),
            dry_run=dry_run,
        )

    def _read_csv_rows(
        self,
        *,
        file_path: Path,
        expected_headers: tuple[str, ...],
        rejections: list[RejectedImportRow],
    ) -> list[tuple[int, dict[str, str | None]]]:
        if not file_path.exists():
            rejections.append(
                RejectedImportRow(
                    file_path=str(file_path),
                    line_number=1,
                    domain=None,
                    reason="CSV file does not exist",
                )
            )
            return []

        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = tuple(reader.fieldnames or ())
            if header != expected_headers:
                rejections.append(
                    RejectedImportRow(
                        file_path=str(file_path),
                        line_number=1,
                        domain=None,
                        reason=(f"Expected headers {expected_headers!r} but found {header!r}"),
                    )
                )
                return []
            return [(line_number, row) for line_number, row in enumerate(reader, start=2)]

    def _required_value(
        self,
        *,
        raw_row: dict[str, str | None],
        key: str,
        file_path: Path,
        line_number: int,
    ) -> str:
        value = self._optional_value(raw_row=raw_row, key=key)
        if value is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Missing required value for '{key}' at {file_path}:{line_number}",
            )
        return value

    def _optional_value(self, *, raw_row: dict[str, str | None], key: str) -> str | None:
        raw_value = raw_row.get(key)
        if raw_value is None:
            return None
        cleaned = raw_value.strip()
        return cleaned or None

    def _parse_bool(self, *, raw_value: str) -> bool:
        normalized = raw_value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Boolean fields must be 'true' or 'false'",
        )

    def _allowed_rows_equal(self, *, existing: AllowedDomain, seed: _AllowedSeedRow) -> bool:
        return (
            existing.org_type == seed.org_type
            and existing.org_name == seed.org_name
            and existing.source == seed.source
            and existing.source_ref == seed.source_ref
            and existing.is_active == seed.is_active
            and existing.notes == seed.notes
        )

    def _blocked_rows_equal(self, *, existing: BlockedDomain, seed: _BlockedSeedRow) -> bool:
        return (
            existing.reason == seed.reason
            and existing.source == seed.source
            and existing.source_ref == seed.source_ref
            and existing.is_active == seed.is_active
            and existing.notes == seed.notes
        )

    def _rejection_summary(
        self,
        *,
        label: str,
        total_rows: int,
        rejections: list[RejectedImportRow],
        dry_run: bool,
    ) -> ImportSummary:
        return ImportSummary(
            label=label,
            total_rows=total_rows,
            inserted=0,
            updated=0,
            unchanged=0,
            rejected_rows=tuple(rejections),
            dry_run=dry_run,
        )
