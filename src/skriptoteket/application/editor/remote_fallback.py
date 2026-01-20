from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RemoteFallbackConsent:
    """Tri-state user consent for remote providers.

    - `True`: user explicitly allows remote providers (when admin policy allows).
    - `False`: user explicitly denies remote providers.
    - `None`: user has not decided (treat as deny for execution; optionally prompt).
    """

    allow_remote_fallback: bool | None
    remote_providers_enabled: bool

    @property
    def remote_allowed(self) -> bool:
        return self.remote_providers_enabled and self.allow_remote_fallback is True

    @property
    def should_prompt(self) -> bool:
        return self.remote_providers_enabled and self.allow_remote_fallback is None
