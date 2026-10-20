/**
 * Mina filer record paths (TASK-SKRIPT-41-02-06, U4).
 *
 * Domain purpose:
 *   One place naming the vault download and delete paths, shared by the
 *   Mina filer list and the exam workspace unreadable rows so both address
 *   the same stored file.
 */

export function vaultFileDownloadPath(vaultFileId: string): string {
  return `/api/v1/vault/files/${encodeURIComponent(vaultFileId)}/download`;
}

export function vaultFileDeletePath(vaultFileId: string): string {
  return `/api/v1/vault/files/${encodeURIComponent(vaultFileId)}/delete`;
}
