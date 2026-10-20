/**
 * Unreadable saved exams transport (TASK-SKRIPT-41-02-06, U4).
 *
 * Domain purpose:
 *   Thin typed client for the teacher's saved exams in a format the app
 *   cannot read: list them through the unreadable-documents route, download
 *   a stored head file unchanged through the shared vault download path,
 *   and move it to the papperskorg through the shared vault delete path.
 *
 * Relationships:
 *   - Uses `api/client.ts` helpers and the vault paths in
 *     `api/vaultFilePaths.ts`.
 *   - Types come from the generated OpenAPI schema (`api/openapi.d.ts`).
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceUnreadableFiles.ts`.
 */

import { apiFetchBlobResponse, apiGet, apiPost } from "./client";
import type { ApiBlobResponse } from "./client";
import { vaultFileDeletePath, vaultFileDownloadPath } from "./vaultFilePaths";
import type { components } from "./openapi";

type Schemas = components["schemas"];

export type ExamWorkspaceUnreadableDocument = Schemas["ExamWorkspaceUnreadableDocument"];
export type ExamWorkspaceUnreadableDocumentListResponse =
  Schemas["ExamWorkspaceUnreadableDocumentListResponse"];
export type VaultFileInfo = Schemas["VaultFileInfo"];

type DeleteVaultFileResult = Schemas["DeleteVaultFileResult"];

const UNREADABLE_DOCUMENTS_PATH =
  "/api/v1/apps/documents.conversion_hub/exam-workspace/unreadable-documents";

export async function listUnreadableExamWorkspaceDocuments(): Promise<ExamWorkspaceUnreadableDocumentListResponse> {
  return await apiGet<ExamWorkspaceUnreadableDocumentListResponse>(UNREADABLE_DOCUMENTS_PATH);
}

/** Fetch the stored head file unchanged; the caller names the download from the response. */
export async function downloadSavedExamFile(vaultFileId: string): Promise<ApiBlobResponse> {
  return await apiFetchBlobResponse(vaultFileDownloadPath(vaultFileId));
}

/** Move the stored head file to the papperskorg with one click, like any other Mina filer delete. */
export async function removeSavedExamFile(vaultFileId: string): Promise<VaultFileInfo> {
  const result = await apiPost<DeleteVaultFileResult>(vaultFileDeletePath(vaultFileId));
  return result.file;
}
