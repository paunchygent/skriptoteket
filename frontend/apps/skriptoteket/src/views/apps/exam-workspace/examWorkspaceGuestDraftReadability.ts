/**
 * Guest draft readability from the generated format constants.
 *
 * Domain purpose:
 *   Decide whether a stored browser draft the app can open: every stored
 *   document's schema version must be exactly the current native exam
 *   document version. The browser runs no upgrade steps, so one older (or
 *   unknown) document anywhere makes the whole draft unopenable and the
 *   caller shows the download-or-remove notice instead of the editor.
 *
 * Relationships:
 *   - Reads the generated `api/nativeExamDocumentVersions` constants, the
 *     one browser source built from the Python domain truth; no competing
 *     oldest-readable constant lives here.
 *   - Consumed by the guest store admission and the handoff controller's
 *     reason mapping; the signed-out host reads it before mounting the
 *     editor.
 */

import {
  CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
  NATIVE_EXAM_DOCUMENT_SCHEMA_PREFIX,
} from "../../../api/nativeExamDocumentVersions.generated";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";

/** The one schema version the browser opens: the prefix plus the current version. */
export function currentNativeExamDocumentSchemaVersion(): string {
  return `${NATIVE_EXAM_DOCUMENT_SCHEMA_PREFIX}${CURRENT_NATIVE_EXAM_DOCUMENT_VERSION}`;
}

/**
 * Every stored document must carry the current schema version: the saved
 * copy, the baseline and every undo step. Anything else is unopenable, so
 * the caller shows the download-or-remove notice instead of the editor.
 */
export function isGuestDraftReadable(draft: ExamWorkspaceGuestDraft): boolean {
  const expected = currentNativeExamDocumentSchemaVersion();
  const documents = [draft.saved_document, draft.baseline.document];
  for (const step of draft.steps) {
    documents.push(step.document);
  }
  return documents.every((document) => document.schema_version === expected);
}
