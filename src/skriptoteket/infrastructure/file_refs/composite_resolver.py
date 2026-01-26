from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.scripting.file_refs import FileRef, FileRefSource, parse_file_ref
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.protocols.file_refs import FileRefEntry, FileRefResolverProtocol


class CompositeFileRefResolver(FileRefResolverProtocol):
    def __init__(
        self,
        *,
        session_resolver: FileRefResolverProtocol,
        vault_resolver: FileRefResolverProtocol,
    ) -> None:
        self._session_resolver = session_resolver
        self._vault_resolver = vault_resolver

    async def list_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        sources: list[FileRefSource],
    ) -> list[FileRefEntry]:
        normalized_sources = _normalize_sources(sources)
        refs: list[FileRefEntry] = []
        if FileRefSource.SESSION in normalized_sources:
            refs.extend(
                await self._session_resolver.list_refs(
                    tool_id=tool_id,
                    user_id=user_id,
                    context=context,
                    sources=[FileRefSource.SESSION],
                )
            )
        if FileRefSource.VAULT in normalized_sources:
            refs.extend(
                await self._vault_resolver.list_refs(
                    tool_id=tool_id,
                    user_id=user_id,
                    context=context,
                    sources=[FileRefSource.VAULT],
                )
            )
        return refs

    async def resolve_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        refs_by_field: dict[str, list[FileRef]],
    ) -> list[ResolvedInputFile]:
        if not refs_by_field:
            return []

        session_refs: dict[str, list[FileRef]] = {}
        vault_refs: dict[str, list[FileRef]] = {}

        for field, refs in refs_by_field.items():
            for ref in refs:
                source, _value = parse_file_ref(value=ref)
                if source is FileRefSource.VAULT:
                    vault_refs.setdefault(field, []).append(ref)
                else:
                    session_refs.setdefault(field, []).append(ref)

        resolved: list[ResolvedInputFile] = []
        if session_refs:
            resolved.extend(
                await self._session_resolver.resolve_refs(
                    tool_id=tool_id,
                    user_id=user_id,
                    context=context,
                    refs_by_field=session_refs,
                )
            )
        if vault_refs:
            resolved.extend(
                await self._vault_resolver.resolve_refs(
                    tool_id=tool_id,
                    user_id=user_id,
                    context=context,
                    refs_by_field=vault_refs,
                )
            )
        return resolved


def _normalize_sources(sources: list[FileRefSource]) -> set[FileRefSource]:
    if not sources:
        return {FileRefSource.SESSION, FileRefSource.VAULT}
    return set(sources)
