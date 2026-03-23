"""Protocols for the Flunk-Out Frenzy curated app contract.

These protocols keep the bespoke game bootstrap flow protocol-first so the web
layer can depend on abstractions while the application layer owns the payload
shape.
"""

from __future__ import annotations

from typing import Protocol

from skriptoteket.application.curated_apps.flunk_out_frenzy import FlunkOutFrenzyBootstrapResult
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition


class FlunkOutFrenzyBootstrapHandlerProtocol(Protocol):
    """Build the minimal bootstrap payload for the bespoke game shell."""

    async def handle(self, *, app: CuratedAppDefinition) -> FlunkOutFrenzyBootstrapResult: ...
