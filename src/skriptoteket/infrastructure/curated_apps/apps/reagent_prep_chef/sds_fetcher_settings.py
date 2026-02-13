from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

ProgressReporter = Callable[[str, dict[str, object]], None]


@dataclass(frozen=True, slots=True)
class SdsFetcherSettings:
    """Shared settings for SDS fetchers (PubChem + SDS PDF)."""

    timeout_seconds: float
    user_agent: str
    retry_attempts: int = 3
    retry_backoff_seconds: float = 0.5
    retry_backoff_max_seconds: float = 5.0
    sds_required: bool = True
    require_pubchem_cid: bool = False
    cid_candidate_limit: int = 25
    autocomplete_limit: int = 10
