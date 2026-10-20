/**
 * Skriptoteket-owned exam workspace transport.
 *
 * Domain purpose:
 *   Thin typed client for the teacher exam workspace document lifecycle:
 *   import a .docx exam, a DigiExam .dxe or a QTI .zip package, list and
 *   reopen saved documents, save versioned revisions, download on-demand
 *   exports, list what Exam.net loses on import, and request AI answer-key
 *   suggestions for the questions exactly as the editor shows them.
 *
 * Relationships:
 *   - Uses `api/client.ts` helpers for protected API calls.
 *   - Types come from the generated OpenAPI schema (`api/openapi.d.ts`).
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceDocument.ts`,
 *     `useExamWorkspaceExports.ts`, and `useExamWorkspaceEnrichment.ts`.
 */

import { apiFetch, apiGet, apiPatch, apiPost, resolveProtectedApiUrl } from "./client";
import type { AuthSession } from "../stores/auth";
import type { components } from "./openapi";

type Schemas = components["schemas"];

const ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace";

export type NativeExamDocument = Schemas["NativeExamDocument-Output"];
export type ExamCourseChoice = Schemas["ExamCourseChoice"];
export type NativeExamHeader = Schemas["NativeExamHeader"];
export type NativeExamItem = Schemas["NativeExamItem-Output"];
export type NativeExamParent = Schemas["NativeExamParent-Output"];
export type NativeExamBodyParagraph = Schemas["NativeParagraph"];
export type NativeExamBodySegment = NativeExamBodyParagraph["segments"][number];
export type NativeExamItemKind = Schemas["NativeExamItemKind"];
export type NativeExamChoice = Schemas["NativeChoice-Output"];
export type NativeExamCriterion = Schemas["NativeExamCriterion"];
export type NativeExamMatchLeft = Schemas["NativeMatchLeft-Output"];
export type NativeExamMatchRight = Schemas["NativeMatchRight-Output"];
export type NativeExamMatchPair = Schemas["NativeMatchPair"];
export type NativeExamGap = Schemas["NativeGap-Output"];
export type NativeExamAnswerKeyOrigin = Schemas["NativeAnswerKeyOrigin"];
export type NativeExamAnswerKey = Schemas["NativeAnswerKey"];
export type NativeExamReviewState = Schemas["NativeItemReviewState"];
export type NativeExamParseOrigin = Schemas["NativeParseOrigin"];
export type NativeExamItemReview = Schemas["NativeItemReview"];
export type NativeExamAsset = Schemas["NativeExamAsset"];

export type ExamWorkspaceDocumentSummary = Schemas["ExamWorkspaceDocumentSummary"];
export type ExamCourse = Schemas["ExamCourse"];
export type ExamCourseCatalogResponse = Schemas["ExamCourseCatalogResponse"];
export type ExamWorkspaceDocumentResponse = Schemas["ExamWorkspaceDocumentResponse"];
/** A deletion's document response; `removed_parent_id` names an instruction that went with it. */
export type ExamWorkspaceDeleteResponse = Schemas["ExamWorkspaceDeleteResponse"];
/** A part creation's document response; `created_parent_id` names the part the editor opens. */
export type ExamWorkspaceCreatedPartResponse = Schemas["ExamWorkspaceCreatedPartResponse"];
export type ExamWorkspaceDocumentListResponse = Schemas["ExamWorkspaceDocumentListResponse"];
export type ExamWorkspaceEnrichmentState = Schemas["ExamWorkspaceEnrichmentState"];
export type ExamWorkspaceAnswerKeySuggestionsStatus =
  Schemas["ExamWorkspaceAnswerKeySuggestionsResponse"];
export type ExamWorkspaceConversionStatus = Schemas["ExamWorkspaceConversionStatus"];
export type ExamWorkspaceConversionUnit = Schemas["ExamWorkspaceConversionUnit"];
export type NativeAnswerKeySuggestion = Schemas["NativeAnswerKeySuggestion"];
export type ExamWorkspaceAnswerKeySuggestionItem =
  Schemas["ExamWorkspaceAnswerKeySuggestionItem"];
export type ExamWorkspaceItemRetryResponse = Schemas["ExamWorkspaceItemRetryResponse"];
export type ExamWorkspaceMisspellingsRequest = Schemas["ExamWorkspaceMisspellingsRequest"];
export type ExamWorkspaceMisspellingsResponse = Schemas["ExamWorkspaceMisspellingsResponse"];
export type ExamWorkspaceDocumentGroup = Schemas["ExamWorkspaceDocumentGroup"];
export type ExamListOrdering = Schemas["UpdateExamListOrderingRequest"]["ordering"];
export type ExamWorkspaceHistory = Schemas["ExamWorkspaceHistoryResponse"];
export type ExamWorkspaceHistoryDocument = Schemas["ExamWorkspaceHistoryDocumentResponse"];
export type ExamWorkspaceUndoStep = Schemas["ExamWorkspaceUndoStepResponse"];
export type NativeExamContentTag = Schemas["NativeExamContentTag"];
export type ExamCourseContent = Schemas["ExamCourseContentResponse"];
export type ExamWorkspaceContentSuggestions = Schemas["ContentSuggestionsResponse"];
export type NativeExamImportRecord = Schemas["NativeExamImportRecord-Output"];
export type ChangeExamWorkspaceItemTypeResponse = Schemas["ChangeExamWorkspaceItemTypeResponse"];

export type ExamWorkspaceUndoStepParams = {
  expectedCursor: string;
  document: NativeExamDocument;
  afterStepId: string | null;
  tabId: string;
};

export type MoveExamWorkspaceHistoryPositionParams = {
  expectedCursor: string;
  stepId: string;
  tabId: string;
};

/**
 * Protected path of one exam workspace document, shared by the transport
 * modules that build on this document root.
 */
export function documentPath(lineageId: string): string {
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
  courseKey: string | null = null,
): Promise<ExamWorkspaceConversionStatus> {
  const form = new FormData();
  form.append("file", file, file.name);
  if (courseKey) {
    form.append("course_key", courseKey);
  }
  return await apiPost<ExamWorkspaceConversionStatus>(`${ROOT}/documents`, form);
}

export async function getExamCourseCatalog(): Promise<ExamCourseCatalogResponse> {
  return await apiGet<ExamCourseCatalogResponse>(`${ROOT}/courses`);
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

export async function moveExamWorkspaceHistoryPosition(
  lineageId: string,
  params: MoveExamWorkspaceHistoryPositionParams,
): Promise<ExamWorkspaceUndoStep> {
  const body: Schemas["MoveExamWorkspaceHistoryPositionRequest"] = {
    expected_cursor: params.expectedCursor,
    step_id: params.stepId,
    tab_id: params.tabId,
  };
  return await apiPost<ExamWorkspaceUndoStep>(`${documentPath(lineageId)}/history/position`, body);
}

export type ExamWorkspaceEditLeaseResponse = Schemas["ExamWorkspaceEditLeaseResponse"];

function editLeasePath(lineageId: string, operation: string): string {
  return `${documentPath(lineageId)}/edit-lease/${operation}`;
}

/** Take the exam's edit lease for one tab; a live foreign lease refuses with 409. */
export async function claimExamWorkspaceEditLease(
  lineageId: string,
  tabId: string,
): Promise<ExamWorkspaceEditLeaseResponse> {
  const body: Schemas["ExamWorkspaceEditLeaseRequest"] = { tab_id: tabId };
  return await apiPost<ExamWorkspaceEditLeaseResponse>(editLeasePath(lineageId, "claim"), body);
}

/** Refresh the holder's lease; the response names a waiting takeover tab. */
export async function renewExamWorkspaceEditLease(
  lineageId: string,
  tabId: string,
): Promise<ExamWorkspaceEditLeaseResponse> {
  const body: Schemas["ExamWorkspaceEditLeaseRequest"] = { tab_id: tabId };
  return await apiPost<ExamWorkspaceEditLeaseResponse>(editLeasePath(lineageId, "renew"), body);
}

/** Ask for the lease; the holder sees the request at its next heartbeat. */
export async function requestExamWorkspaceEditLeaseTakeover(
  lineageId: string,
  tabId: string,
): Promise<ExamWorkspaceEditLeaseResponse> {
  const body: Schemas["ExamWorkspaceEditLeaseRequest"] = { tab_id: tabId };
  return await apiPost<ExamWorkspaceEditLeaseResponse>(editLeasePath(lineageId, "takeover"), body);
}

/** Clear the holder's lease; a waiting takeover claims it next. */
export async function releaseExamWorkspaceEditLease(
  lineageId: string,
  tabId: string,
  options: { keepalive?: boolean } = {},
): Promise<ExamWorkspaceEditLeaseResponse> {
  const body: Schemas["ExamWorkspaceEditLeaseRequest"] = { tab_id: tabId };
  if (options.keepalive === true) {
    // A `pagehide` release must survive the unload: `keepalive` lets the
    // browser finish the POST after the page is gone. `sendBeacon` cannot
    // carry the CSRF header, so it cannot use this transport.
    return await apiFetch<ExamWorkspaceEditLeaseResponse>(editLeasePath(lineageId, "release"), {
      body,
      keepalive: true,
      method: "POST",
    });
  }
  return await apiPost<ExamWorkspaceEditLeaseResponse>(editLeasePath(lineageId, "release"), body);
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

/**
 * Ask the deterministic producer for the automatic misspellings of newly
 * keyed accepted answers. The request carries only the values this edit
 * added, every accepted answer the question now holds (so the producer never
 * proposes one gold answer as another's misspelling), and the document's text
 * for its language.
 */
export async function requestExamWorkspaceAnswerMisspellings(
  request: ExamWorkspaceMisspellingsRequest,
): Promise<ExamWorkspaceMisspellingsResponse> {
  return await apiPost<ExamWorkspaceMisspellingsResponse>(
    `${ROOT}/answer-misspellings`,
    request,
  );
}

/** Store the editor's document as the newest undo step; `afterStepId` branches after an undo. */
export async function storeExamWorkspaceUndoStep(
  lineageId: string,
  params: ExamWorkspaceUndoStepParams,
): Promise<ExamWorkspaceUndoStep> {
  const body: Schemas["StoreExamWorkspaceUndoStepRequest"] = {
    after_step_id: params.afterStepId,
    document: params.document,
    expected_cursor: params.expectedCursor,
    tab_id: params.tabId,
  };
  return await apiPost<ExamWorkspaceUndoStep>(`${documentPath(lineageId)}/autosaves`, body);
}

export async function getExamWorkspaceHistory(lineageId: string): Promise<ExamWorkspaceHistory> {
  return await apiGet<ExamWorkspaceHistory>(`${documentPath(lineageId)}/history`);
}

export async function getExamWorkspaceHistoryStep(
  lineageId: string,
  stepId: string,
): Promise<ExamWorkspaceHistoryDocument> {
  return await apiGet<ExamWorkspaceHistoryDocument>(
    `${documentPath(lineageId)}/history/${encodeURIComponent(stepId)}`,
  );
}

/** Spara som: a new exam with its own file, the given name and an empty undo history. */
export async function copyExamWorkspaceDocument(
  lineageId: string,
  name: string,
  document: NativeExamDocument,
): Promise<ExamWorkspaceDocumentResponse> {
  const body: Schemas["SaveAsExamWorkspaceDocumentRequest"] = { document, name };
  return await apiPost<ExamWorkspaceDocumentResponse>(`${documentPath(lineageId)}/copy`, body);
}

/**
 * Import a QTI package (.zip). The package is read at once into a saved
 * document; the response is its summary, which the caller opens like a
 * document from the Öppna list.
 */
export async function importExamWorkspaceQti(
  file: File,
  courseKey: string | null = null,
): Promise<ExamWorkspaceDocumentSummary> {
  const form = new FormData();
  form.append("file", file, file.name);
  if (courseKey) {
    form.append("course_key", courseKey);
  }
  return await apiPost<ExamWorkspaceDocumentSummary>(`${ROOT}/import-qti`, form);
}

/** Import a DigiExam export (.dxe); conversion runs in the background like a Word import. */
export async function importExamWorkspaceDigiExam(
  file: File,
  courseKey: string | null = null,
): Promise<ExamWorkspaceConversionStatus> {
  const form = new FormData();
  form.append("file", file, file.name);
  if (courseKey) {
    form.append("course_key", courseKey);
  }
  return await apiPost<ExamWorkspaceConversionStatus>(`${ROOT}/import-digiexam`, form);
}

/** The course's central content, one checklist entry per item. */
export async function getExamCourseContent(courseKey: string): Promise<ExamCourseContent> {
  return await apiGet<ExamCourseContent>(`${ROOT}/courses/${courseKey.split("/").map(encodeURIComponent).join("/")}/content`);
}

/** Suggest central content from the saved exam file; save a changed course first. */
export async function requestExamWorkspaceContentSuggestions(
  lineageId: string,
): Promise<ExamWorkspaceContentSuggestions> {
  return await apiPost<ExamWorkspaceContentSuggestions>(
    `${documentPath(lineageId)}/content-suggestions`,
  );
}

export async function getExamWorkspaceContentSuggestions(
  lineageId: string,
  jobId: string,
): Promise<ExamWorkspaceContentSuggestions> {
  return await apiGet<ExamWorkspaceContentSuggestions>(
    `${documentPath(lineageId)}/content-suggestions/${encodeURIComponent(jobId)}`,
  );
}

/** Remember how the teacher sorts the Öppna exam list. */
export async function updateExamListOrdering(ordering: ExamListOrdering): Promise<void> {
  const body: Schemas["UpdateExamListOrderingRequest"] = { ordering };
  await apiPatch<unknown>("/api/v1/profile/exam-list-ordering", body);
}

/**
 * Save the signed-out browser draft into Mina filer once per handoff key.
 *
 * The multipart body carries the `draft_id` idempotency key, the `document`
 * JSON of the newest edits, the `notes` JSON of the parser's import notes,
 * and one `asset:<id>` file part per picture the document declares; stored
 * bytes the document no longer names are never sent. `handoffKey` identifies
 * one browser snapshot: the caller passes the snapshot's cursor, so the
 * server claims once per (user, key) and a later handoff of newer edits
 * imports its own exam. `binding` carries the handoff owner's auth
 * lifetime and the superseded-success signal: a replaced sign-in fails as
 * `SupersededAuthSessionError` instead of posting under the new teacher,
 * and a 2xx answered after retirement reports through
 * `onSupersededSuccess` so the caller can clear the posted snapshot.
 */
export async function importExamWorkspaceGuestDraft(
  handoffKey: string,
  document: NativeExamDocument,
  assets: Record<string, Blob>,
  notes: ExamWorkspaceDocumentResponse["notes"],
  binding: { session: AuthSession; onSupersededSuccess: () => void },
): Promise<ExamWorkspaceDocumentResponse> {
  const form = new FormData();
  form.append("draft_id", handoffKey);
  form.append("document", JSON.stringify(document));
  form.append("notes", JSON.stringify(notes));
  for (const asset of document.assets) {
    const blob = assets[asset.asset_id];
    if (!blob) {
      throw new Error(
        `The import request is missing the picture bytes for asset ${asset.asset_id}.`,
      );
    }
    form.append(`asset:${asset.asset_id}`, blob);
  }
  return await apiFetch<ExamWorkspaceDocumentResponse>(`${ROOT}/guest-drafts`, {
    body: form,
    method: "POST",
    onSupersededSuccess: binding.onSupersededSuccess,
    session: binding.session,
  });
}
