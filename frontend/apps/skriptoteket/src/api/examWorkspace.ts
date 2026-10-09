/**
 * Skriptoteket-owned exam workspace transport.
 *
 * Domain purpose:
 *   Thin typed client for the teacher exam workspace document lifecycle:
 *   import a .docx exam, read a document lineage back, and save versioned
 *   revisions of the native exam document.
 *
 * Relationships:
 *   - Uses `api/client.ts` helpers for protected API calls.
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceDocument.ts`.
 *   - Local hand-written types; generated openapi types for these routes do
 *     not exist yet, so shapes mirror the backend contract exactly.
 */

import { apiGet, apiPost, apiPut } from "./client";

const ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace";

export type NativeExamBodySegment =
  | { kind: "text"; text: string }
  | { kind: "gap"; gap_id: string }
  | { kind: "asset"; asset_id: string };

export type NativeExamBodyParagraph = {
  segments: NativeExamBodySegment[];
};

export type NativeExamItemKind =
  | "free_text"
  | "single_choice"
  | "multiple_response"
  | "gap_fill";

export type NativeExamChoice = {
  choice_id: string;
  text: string;
};

export type NativeExamGap = {
  gap_id: string;
  accepted_values: string[];
  hint: string | null;
};

export type NativeExamAnswerKeyOrigin =
  | "absent"
  | "not_applicable"
  | "source_provided"
  | "teacher_authored"
  | "machine_proposed"
  | "reviewed_advisory";

export type NativeExamAnswerKey = {
  origin: NativeExamAnswerKeyOrigin;
  correct_choice_ids: string[];
};

export type NativeExamReviewState = "review_required" | "review_complete";

export type NativeExamParseOrigin = "deterministic" | "llm_parsed" | "teacher_created";

export type NativeExamItemReview = {
  state: NativeExamReviewState;
  parse_origin: NativeExamParseOrigin;
  confidence: number | null;
  reasons: string[];
};

export type NativeExamItem = {
  item_id: string;
  sequence: number;
  kind: NativeExamItemKind;
  title: string | null;
  body: NativeExamBodyParagraph[];
  points: number | null;
  choices: NativeExamChoice[];
  gaps: NativeExamGap[];
  answer_key: NativeExamAnswerKey;
  review: NativeExamItemReview;
  source_anchor: string | null;
};

export type NativeExamDocumentOrigin = {
  kind: "docx_import" | "created";
  source_filename?: string | null;
  source_sha256?: string | null;
  extractor_version?: string | null;
};

export type NativeExamDocument = {
  schema_version: "native_exam_document_v1";
  document_id: string;
  revision: number;
  title: string;
  instructions: string[];
  items: NativeExamItem[];
  assets: [];
  origin: NativeExamDocumentOrigin;
};

export type ExamWorkspaceDocumentSummary = {
  lineage_id: string;
  version: number;
  vault_file_id: string;
  name: string;
  saved_at: string;
};

export type ExamWorkspaceDocumentResponse = {
  document: NativeExamDocument;
  summary: ExamWorkspaceDocumentSummary;
  notes: string[];
};

export type SaveExamWorkspaceDocumentParams = {
  expectedRevision: number;
  document: NativeExamDocument;
};

function documentPath(lineageId: string): string {
  return `${ROOT}/documents/${encodeURIComponent(lineageId)}`;
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
  return await apiPut<ExamWorkspaceDocumentResponse>(documentPath(lineageId), {
    expected_revision: params.expectedRevision,
    document: params.document,
  });
}
