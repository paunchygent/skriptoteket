from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.promotions import PromotionEnvelope


class PromotionApplierProtocol(Protocol):
    async def apply_session_promotions(
        self,
        *,
        run_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        artifacts_manifest: ArtifactsManifest,
        promotions: PromotionEnvelope,
    ) -> None: ...
