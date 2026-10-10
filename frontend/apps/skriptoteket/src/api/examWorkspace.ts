/**
 * Skriptoteket-owned exam workspace transport.
 *
 * Domain purpose:
 *   Thin typed client for the teacher exam workspace document lifecycle:
 *   import a .docx exam, list and reopen saved documents, save versioned
 *   revisions, download on-demand exports, and request advisory answer-key
 *   proposals for the saved head revision.
 *
 * Relationships:
 *   - Uses `api/client.ts` helpers for protected API calls.
 *   - Types come from the generated OpenAPI schema (`api/openapi.d.ts`).
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceDocument.ts`,
 *     `useExamWorkspaceExports.ts`, and `useExamWorkspaceEnrichment.ts`.
 */

import { apiFetchBlobResponse, apiGet, apiPost, apiPut } from "./client";
import type { ApiBlobResponse } from "./client";
import type { components } from "./openapi";

type Schemas = components["schemas"];

const ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace";

export type NativeExamDocument = Schemas["NativeExamDocument-Output"];
export type NativeExamItem = Schemas["NativeExamItem-Output"];
export type NativeExamBodyParagraph = Schemas["NativeParagraph"];
export type NativeExamBodySegment = NativeExamBodyParagraph["segments"][number];
export type NativeExamItemKind = Schemas["NativeExamItemKind"];
export type NativeExamChoice = Schemas["NativeChoice"];
export type NativeExamGap = Schemas["NativeGap"];
export type NativeExamAnswerKeyOrigin = Schemas["NativeAnswerKeyOrigin"];
export type NativeExamAnswerKey = Schemas["NativeAnswerKey"];
export type NativeExamReviewState = Schemas["NativeItemReviewState"];
export type NativeExamParseOrigin = Schemas["NativeParseOrigin"];
export type NativeExamItemReview = Schemas["NativeItemReview"];

export type ExamWorkspaceDocumentSummary = Schemas["ExamWorkspaceDocumentSummary"];
export type ExamWorkspaceDocumentResponse = Schemas["ExamWorkspaceDocumentResponse"];
export type ExamWorkspaceDocumentListResponse = Schemas["ExamWorkspaceDocumentListResponse"];
export type ExamWorkspaceExportTarget = Schemas["ExamWorkspaceExportTarget"];
export type ExamWorkspaceEnrichmentState = Schemas["ExamWorkspaceEnrichmentState"];
export type ExamWorkspaceEnrichmentStatus = Schemas["ExamWorkspaceEnrichmentStatusResponse"];
export type ExamWorkspaceAnswerKeyProposal = Schemas["ExamWorkspaceAnswerKeyProposalItem"];

/** Reasons the server-side S4 export gate reports per item (422 `details.blockers`). */
export type ExamWorkspaceExportBlockerReason =
  | "review_required"
  | "machine_proposed_key_unreviewed"
  | "missing_points";

export type ExamWorkspaceExportBlocker = {
  item_id: string;
  reason: ExamWorkspaceExportBlockerReason;
};

export type SaveExamWorkspaceDocumentParams = {
  expectedRevision: number;
  document: NativeExamDocument;
};

function documentPath(lineageId: string): string {
  return `${ROOT}/documents/${encodeURIComponent(lineageId)}`;
}

export async function listExamWorkspaceDocuments(): Promise<ExamWorkspaceDocumentListResponse> {
  return await apiGet<ExamWorkspaceDocumentListResponse>(`${ROOT}/documents`);
}

export async function importExamWorkspaceDocument(
  file: File,
): Promise<ExamWorkspaceDocumentResponse> {
  const form = new FormData();
  form.append("file", file, file.name);
  return await apiPost<ExamWorkspaceDocumentResponse>(`${ROOT}/documents`, form);
}

export async function getExamWorkspaceDocument(
  lineageId: string,
): Promise<ExamWorkspaceDocumentResponse> {
  return await apiGet<ExamWorkspaceDocumentResponse>(documentPath(lineageId));
}

export async function saveExamWorkspaceDocument(
  lineageId: string,
  params: SaveExamWorkspaceDocumentParams,
): Promise<ExamWorkspaceDocumentResponse> {
  const body: Schemas["SaveExamWorkspaceDocumentRequest"] = {
    document: params.document,
    expected_revision: params.expectedRevision,
  };
  return await apiPut<ExamWorkspaceDocumentResponse>(documentPath(lineageId), body);
}

export async function downloadExamWorkspaceExport(
  lineageId: string,
  target: ExamWorkspaceExportTarget,
): Promise<ApiBlobResponse> {
  return await apiFetchBlobResponse(
    `${documentPath(lineageId)}/exports/${encodeURIComponent(target)}`,
  );
}

export async function startExamWorkspaceEnrichment(
  lineageId: string,
): Promise<ExamWorkspaceEnrichmentStatus> {
  return await apiPost<ExamWorkspaceEnrichmentStatus>(`${documentPath(lineageId)}/enrichment`);
}

export async function getExamWorkspaceEnrichment(
  lineageId: string,
): Promise<ExamWorkspaceEnrichmentStatus> {
  return await apiGet<ExamWorkspaceEnrichmentStatus>(`${documentPath(lineageId)}/enrichment`);
}
