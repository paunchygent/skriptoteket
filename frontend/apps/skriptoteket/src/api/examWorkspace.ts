/**
 * Skriptoteket-owned exam workspace transport.
 *
 * Domain purpose:
 *   Thin typed client for the teacher exam workspace document lifecycle:
 *   import a .docx exam, list and reopen saved documents, save versioned
 *   revisions, download on-demand exports, and request AI answer-key
 *   suggestions for the questions exactly as the editor shows them.
 *
 * Relationships:
 *   - Uses `api/client.ts` helpers for protected API calls.
 *   - Types come from the generated OpenAPI schema (`api/openapi.d.ts`).
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceDocument.ts`,
 *     `useExamWorkspaceExports.ts`, and `useExamWorkspaceEnrichment.ts`.
 */

import { apiFetchBlobResponse, apiGet, apiPost, apiPut, resolveProtectedApiUrl } from "./client";
import type { ApiBlobResponse } from "./client";
import type { components } from "./openapi";

type Schemas = components["schemas"];

const ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace";

export type NativeExamDocument = Schemas["NativeExamDocument-Output"];
export type NativeExamItem = Schemas["NativeExamItem-Output"];
export type NativeExamParent = Schemas["NativeExamParent"];
export type NativeExamBodyParagraph = Schemas["NativeParagraph"];
export type NativeExamBodySegment = NativeExamBodyParagraph["segments"][number];
export type NativeExamItemKind = Schemas["NativeExamItemKind"];
export type NativeExamChoice = Schemas["NativeChoice"];
export type NativeExamMatchLeft = Schemas["NativeMatchLeft"];
export type NativeExamMatchRight = Schemas["NativeMatchRight"];
export type NativeExamMatchPair = Schemas["NativeMatchPair"];
export type NativeExamGap = Schemas["NativeGap"];
export type NativeExamAnswerKeyOrigin = Schemas["NativeAnswerKeyOrigin"];
export type NativeExamAnswerKey = Schemas["NativeAnswerKey"];
export type NativeExamReviewState = Schemas["NativeItemReviewState"];
export type NativeExamParseOrigin = Schemas["NativeParseOrigin"];
export type NativeExamItemReview = Schemas["NativeItemReview"];
export type NativeExamAsset = Schemas["NativeExamAsset"];

export type ExamWorkspaceDocumentSummary = Schemas["ExamWorkspaceDocumentSummary"];
export type ExamWorkspaceDocumentResponse = Schemas["ExamWorkspaceDocumentResponse"];
export type ExamWorkspaceDocumentListResponse = Schemas["ExamWorkspaceDocumentListResponse"];
export type ExamWorkspaceExportTarget = Schemas["ExamWorkspaceExportTarget"];
export type ExamWorkspaceEnrichmentState = Schemas["ExamWorkspaceEnrichmentState"];
export type ExamWorkspaceAnswerKeySuggestionsStatus =
  Schemas["ExamWorkspaceAnswerKeySuggestionsResponse"];
export type ExamWorkspaceConversionStatus = Schemas["ExamWorkspaceConversionStatus"];
export type ExamWorkspaceConversionUnit = Schemas["ExamWorkspaceConversionUnit"];
export type NativeAnswerKeySuggestion = Schemas["NativeAnswerKeySuggestion"];
export type ExamWorkspaceAnswerKeySuggestionItem =
  Schemas["ExamWorkspaceAnswerKeySuggestionItem"];
export type ExamWorkspaceItemRetryResponse = Schemas["ExamWorkspaceItemRetryResponse"];

/** Reasons the server-side S4 export gate reports per item (422 `details.blockers`). */
export type ExamWorkspaceExportBlockerReason =
  | "unbuilt_question"
  | "machine_proposed_key_unreviewed"
  | "missing_points"
  | "missing_answer_key";

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

/**
 * Protected URL of one declared picture on an exam workspace document.
 *
 * Pictures are content-addressed, so the same asset id always names the same
 * bytes; the optional revision is a cache hint, never part of the picture's
 * identity. The URL goes through the Gateway-aware protected base, never the
 * app host, and the browser's same-site session cookie authorises the GET.
 */
export function examWorkspaceAssetUrl(
  lineageId: string,
  assetId: string,
  revision?: number,
): string {
  const path = `${documentPath(lineageId)}/assets/${encodeURIComponent(assetId)}`;
  const query = revision === undefined ? "" : `?revision=${revision}`;
  return resolveProtectedApiUrl(`${path}${query}`);
}

export async function listExamWorkspaceDocuments(): Promise<ExamWorkspaceDocumentListResponse> {
  return await apiGet<ExamWorkspaceDocumentListResponse>(`${ROOT}/documents`);
}

export async function importExamWorkspaceDocument(
  file: File,
): Promise<ExamWorkspaceConversionStatus> {
  const form = new FormData();
  form.append("file", file, file.name);
  return await apiPost<ExamWorkspaceConversionStatus>(`${ROOT}/documents`, form);
}

export async function getExamWorkspaceConversionStatus(
  jobId: string,
): Promise<ExamWorkspaceConversionStatus> {
  return await apiGet<ExamWorkspaceConversionStatus>(
    `${ROOT}/conversion-jobs/${encodeURIComponent(jobId)}`,
  );
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

/**
 * Request AI suggestions for the editor's current document: one named
 * question when `itemId` is given, otherwise every keyless keyed question.
 */
export async function requestExamWorkspaceAnswerKeySuggestions(
  lineageId: string,
  document: NativeExamDocument,
  itemId?: string,
): Promise<ExamWorkspaceAnswerKeySuggestionsStatus> {
  const body: Schemas["RequestExamWorkspaceAnswerKeySuggestionsRequest"] = {
    document,
    item_id: itemId ?? null,
  };
  return await apiPost<ExamWorkspaceAnswerKeySuggestionsStatus>(
    `${documentPath(lineageId)}/answer-key-suggestions`,
    body,
  );
}

export async function getExamWorkspaceAnswerKeySuggestions(
  lineageId: string,
  jobId: string,
): Promise<ExamWorkspaceAnswerKeySuggestionsStatus> {
  return await apiGet<ExamWorkspaceAnswerKeySuggestionsStatus>(
    `${documentPath(lineageId)}/answer-key-suggestions/${encodeURIComponent(jobId)}`,
  );
}

/** The newest suggestion job requested on this saved version, or null when there is none. */
export async function findExamWorkspaceAnswerKeySuggestions(
  lineageId: string,
  documentRevision: number,
): Promise<ExamWorkspaceAnswerKeySuggestionsStatus | null> {
  return await apiGet<ExamWorkspaceAnswerKeySuggestionsStatus | null>(
    `${documentPath(lineageId)}/answer-key-suggestions?document_revision=${documentRevision}`,
  );
}

/**
 * Reconvert one question from the saved revision's stored source with the
 * teacher's chosen type. The response carries exactly one replacement item;
 * the caller replaces only that item in its draft. A converter problem
 * arrives as a source-review item, not as a failed request.
 */
export async function retryExamWorkspaceItem(
  lineageId: string,
  document: NativeExamDocument,
  itemId: string,
  kind: NativeExamItemKind,
): Promise<ExamWorkspaceItemRetryResponse> {
  const body: Schemas["RetryExamWorkspaceItemRequest"] = {
    document,
    item_id: itemId,
    kind,
  };
  return await apiPost<ExamWorkspaceItemRetryResponse>(
    `${documentPath(lineageId)}/items/retry`,
    body,
  );
}
