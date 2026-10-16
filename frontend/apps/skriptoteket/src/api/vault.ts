/**
 * Mina filer record API (rename, TASK-SKRIPT-39-08-01 / TASK-SKRIPT-37-05-04).
 *
 * Renames one owned record by its stem; the backend keeps the record's extension and
 * renames every version of a document lineage at once.
 */

import { apiPost } from "./client";
import type { components } from "./openapi";

type Schemas = components["schemas"];

export type RenameVaultFileResult = Schemas["RenameVaultFileResult"];

export async function renameVaultFile(
  fileId: string,
  stem: string,
): Promise<RenameVaultFileResult> {
  return await apiPost<RenameVaultFileResult>(
    `/api/v1/vault/files/${encodeURIComponent(fileId)}/rename`,
    { stem },
  );
}
