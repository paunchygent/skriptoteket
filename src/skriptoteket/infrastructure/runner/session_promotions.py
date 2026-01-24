from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.file_refs import build_session_file_ref, parse_file_ref
from skriptoteket.domain.scripting.promotions import PromotionEnvelope, PromotionRequest
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.runner import ArtifactManagerProtocol
from skriptoteket.protocols.session_files import SessionFileStorageProtocol


class SessionPromotionApplier(PromotionApplierProtocol):
    def __init__(
        self,
        *,
        artifacts: ArtifactManagerProtocol,
        session_files: SessionFileStorageProtocol,
    ) -> None:
        self._artifacts = artifacts
        self._session_files = session_files

    async def apply_session_promotions(
        self,
        *,
        run_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        artifacts_manifest: ArtifactsManifest,
        promotions: PromotionEnvelope,
    ) -> None:
        if not promotions.requests:
            return

        artifacts_by_path = {item.path: item for item in artifacts_manifest.artifacts}
        seen_names: set[str] = set()

        files_to_store: list[tuple[str, bytes]] = []
        for request in promotions.requests:
            _require_session_promotion(request=request)
            if request.name in seen_names:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Runner contract violation: duplicate promotion names",
                    details={"name": request.name},
                )
            seen_names.add(request.name)

            expected_ref = build_session_file_ref(name=request.name)
            if request.ref is not None and request.ref != expected_ref:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Runner contract violation: promotion ref mismatch",
                    details={
                        "expected_ref": expected_ref,
                        "ref": request.ref,
                        "name": request.name,
                    },
                )

            if request.source_path not in artifacts_by_path:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Runner contract violation: promotion source missing",
                    details={"source_path": request.source_path},
                )

            content = self._artifacts.read_artifact(
                run_id=run_id,
                artifact_path=request.source_path,
            )
            files_to_store.append((request.name, content))

        await self._session_files.upsert_files(
            tool_id=tool_id,
            user_id=user_id,
            context=context,
            files=files_to_store,
        )


def _require_session_promotion(*, request: PromotionRequest) -> None:
    if request.kind != "session":
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: unsupported promotion kind",
            details={"kind": request.kind},
        )
    if request.ref is not None:
        source, _value = parse_file_ref(value=request.ref)
        if source != "session":
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Runner contract violation: promotion ref must be session:*",
                details={"ref": request.ref},
            )
