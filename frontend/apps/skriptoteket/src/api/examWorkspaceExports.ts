/**
 * Skriptoteket-owned exam workspace export and print transport.
 *
 * Domain purpose:
 *   Thin typed client for the saved revision's on-demand exports and the
 *   student print preview: download an export format or store it in Mina
 *   filer, read what Exam.net loses on import, and render the saved print
 *   copy page by page.
 *
 * Relationships:
 *   - Uses `api/client.ts` helpers and `documentPath` from `api/examWorkspace.ts`.
 *   - Types come from the generated OpenAPI schema (`api/openapi.d.ts`).
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceExports.ts` and
 *     `useExamWorkspacePrintPreview.ts`.
 */

import { apiFetchBlobResponse, apiGet, apiPost } from "./client";
import type { ApiBlobResponse } from "./client";
import { documentPath } from "./examWorkspace";
import type { components } from "./openapi";

type Schemas = components["schemas"];

export type ExamWorkspaceExportTarget = Schemas["ExamWorkspaceExportTarget"];
export type SavedExamExport = Schemas["VaultFile"];

/** Reasons the server-side S4 export gate reports per item (422 `details.blockers`). */
export type ExamWorkspaceItemExportBlockerReason =
  | "unbuilt_question"
  | "machine_proposed_key_unreviewed"
  | "missing_points"
  | "missing_answer_key"
  | "inline_choice_option_heading"
  | "empty_choice"
  | "empty_gap_option"
  | "empty_match_entry"
  | "ordering_too_few_steps"
  | "empty_ordering_step"
  | "too_few_gap_options"
  | "empty_question_text"
  | "no_gaps";

/** Every reason the gate reports; the title reason belongs to the exam, not a question. */
export type ExamWorkspaceExportBlockerReason = ExamWorkspaceItemExportBlockerReason | "title_without_text";

export type ExamWorkspaceExportBlocker = {
  /** Null for a reason that belongs to the exam. */
  item_id: string | null;
  reason: ExamWorkspaceExportBlockerReason;
};

export type ExamWorkspaceExportChecklistCriterion =
  Schemas["ExamWorkspaceExportChecklistCriterion"];
export type ExamWorkspaceExportChecklistEntry =
  | Schemas["ExamWorkspaceExportChecklistFreeTextCriteria"]
  | Schemas["ExamWorkspaceExportChecklistAllOrNothing"]
  | Schemas["ExamWorkspaceExportChecklistRoundedGaps"];
export type ExamWorkspaceExportChecklistResponse =
  Schemas["ExamWorkspaceExportChecklistResponse"];

/** The server names every export after the exam title; a response without that name is a fault. */
export type ExamWorkspaceExportDownload = ApiBlobResponse & { filename: string };

export async function downloadExamWorkspaceExport(
  lineageId: string,
  target: ExamWorkspaceExportTarget,
  expectedRevision: number,
): Promise<ExamWorkspaceExportDownload> {
  const response = await apiFetchBlobResponse(
    `${documentPath(lineageId)}/exports/${encodeURIComponent(target)}?expected_revision=${expectedRevision}`,
  );
  if (response.filename === null) {
    throw new Error("The export response carries no file name in Content-Disposition.");
  }
  return { ...response, filename: response.filename };
}

/**
 * What Exam.net loses when it imports the saved revision: Fritext criteria,
 * all-or-nothing subquestions, and rounded gap values, computed from the QTI
 * items the export itself builds.
 */
export async function getExamWorkspaceExportChecklist(
  lineageId: string,
  expectedRevision: number,
): Promise<ExamWorkspaceExportChecklistResponse> {
  return await apiGet<ExamWorkspaceExportChecklistResponse>(
    `${documentPath(lineageId)}/export-checklist?expected_revision=${expectedRevision}`,
  );
}

/** Save one export format of the saved revision to Mina filer, replacing the earlier one. */
export async function saveExamWorkspaceExport(
  lineageId: string,
  target: ExamWorkspaceExportTarget,
  expectedRevision: number,
): Promise<SavedExamExport> {
  return await apiPost<SavedExamExport>(
    `${documentPath(lineageId)}/exports/${encodeURIComponent(target)}?expected_revision=${expectedRevision}`,
  );
}

/** The saved student print copy as page images, for the Förhandsgranska panel (W5). */
export type ExamWorkspacePrintPreview = Schemas["ExamWorkspacePrintPreviewResponse"];

/**
 * Render the working state the editor stands on into page images: `pages` holds
 * one PNG data URL per printed page in print order, and `question_pages` maps
 * a question's item id to the 0-based page it first appears on, so the
 * Förhandsgranska panel can scroll to the selected question. `status`
 * "blocked" means the exam cannot be rendered at all. The saved head revision
 * and the history `expectedCursor` both guard the render: a revision or cursor
 * the server has moved past answers 409.
 */
export async function fetchExamWorkspacePrintPreview(
  lineageId: string,
  expectedRevision: number,
  expectedCursor: string,
): Promise<ExamWorkspacePrintPreview> {
  return await apiGet<ExamWorkspacePrintPreview>(
    `${documentPath(lineageId)}/print-preview?expected_revision=${expectedRevision}&expected_cursor=${encodeURIComponent(expectedCursor)}`,
  );
}
