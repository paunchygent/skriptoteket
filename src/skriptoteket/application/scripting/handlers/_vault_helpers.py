from __future__ import annotations

from skriptoteket.application.scripting.vault import VaultFileInfo, VaultUsageInfo
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.file_refs import build_vault_file_ref
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage


def build_vault_file_info(
    *,
    vault_file: VaultFile,
    source_label: str | None = None,
    is_missing_on_disk: bool = False,
) -> VaultFileInfo:
    return VaultFileInfo(
        id=vault_file.id,
        ref=build_vault_file_ref(file_id=vault_file.id),
        name=vault_file.name,
        bytes=vault_file.bytes,
        source_label=source_label,
        is_missing_on_disk=is_missing_on_disk,
        created_at=vault_file.created_at,
        deleted_at=vault_file.deleted_at,
    )


def build_vault_usage_info(
    *,
    usage: VaultUsage | None,
    settings: Settings,
) -> VaultUsageInfo:
    bytes_total = usage.bytes_total if usage else 0
    return VaultUsageInfo(
        bytes_total=bytes_total,
        max_total_bytes=settings.VAULT_MAX_TOTAL_BYTES,
        max_file_bytes=settings.VAULT_MAX_FILE_BYTES,
    )
