"""Registration-domain normalization and allowlist validation services.

Purpose:
  Normalize school-sector email domains in one place and provide the
  registration allow/block decision that later handlers can reuse.

Relationships:
  - Depends on allowlist/blocklist repository protocols.
  - Used by the CSV importer for strict root-domain validation.
"""

from __future__ import annotations

import re

import tldextract

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.identity import (
    AllowedDomainRepositoryProtocol,
    BlockedDomainRepositoryProtocol,
    DomainValidatorProtocol,
)

_INVALID_DOMAIN_CHARS_RE = re.compile(r"[/\s]")


class TldextractDomainValidator(DomainValidatorProtocol):
    """Normalize and validate registration domains with a snapshot-backed PSL."""

    def __init__(
        self,
        *,
        allowed_domains: AllowedDomainRepositoryProtocol,
        blocked_domains: BlockedDomainRepositoryProtocol,
    ) -> None:
        self._allowed_domains = allowed_domains
        self._blocked_domains = blocked_domains
        self._extractor = tldextract.TLDExtract(
            suffix_list_urls=(),
            fallback_to_snapshot=True,
            cache_dir=None,
        )

    def normalize_seed_domain(self, domain: str) -> str:
        candidate = self._canonicalize_domain_candidate(domain)
        root_domain = self._extract_root_domain(candidate)
        if root_domain != candidate:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Importer rows must contain registered/root domains only",
                details={"domain": domain, "normalized_domain": root_domain},
            )
        return root_domain

    def extract_root_domain_from_email(self, email: str) -> str:
        normalized_email = email.strip().lower()
        if normalized_email.count("@") != 1:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ogiltig e-postadress",
                details={"email": email},
            )
        _, host = normalized_email.rsplit("@", 1)
        candidate = self._canonicalize_domain_candidate(host)
        return self._extract_root_domain(candidate)

    async def validate_registration_email(self, email: str) -> None:
        root_domain = self.extract_root_domain_from_email(email)

        blocked = await self._blocked_domains.get_by_domain(root_domain)
        if blocked is not None and blocked.is_active:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="E-postdomänen är inte tillåten för registrering",
                details={"domain": root_domain, "reason": blocked.reason},
            )

        allowed = await self._allowed_domains.get_by_domain(root_domain)
        if allowed is not None and allowed.is_active:
            return

        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="E-postdomänen är inte godkänd för registrering",
            details={"domain": root_domain},
        )

    def _canonicalize_domain_candidate(self, candidate: str) -> str:
        normalized = candidate.strip().lower().strip(".")
        if not normalized:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Domän måste anges",
            )
        if "@" in normalized:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ange endast domännamn, inte en e-postadress",
                details={"domain": candidate},
            )
        if _INVALID_DOMAIN_CHARS_RE.search(normalized):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ogiltigt domänformat",
                details={"domain": candidate},
            )
        return normalized

    def _extract_root_domain(self, candidate: str) -> str:
        extract_result = self._extractor(candidate)
        root_domain = extract_result.top_domain_under_public_suffix
        if not root_domain:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ogiltigt domänformat",
                details={"domain": candidate},
            )
        return root_domain.lower()
