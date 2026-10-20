/**
 * Guest exam workspace store errors.
 *
 * Domain purpose:
 *   The server-shaped refusals the browser store reports when the local
 *   draft disagrees with the editor: a stale cursor or revision is the
 *   server's 409, a document the save rules refuse its 422, an unknown
 *   lineage its 404, and a 429 from the public routes the hourly guest
 *   limit the view answers with the sign-in prompt.
 *
 * Relationships:
 *   - Built on the `ApiError` shape of `api/client.ts` so the workspace UI
 *     cannot tell a browser refusal from the server one it mirrors.
 *   - Used by `examWorkspaceGuestStore.ts` and
 *     `examWorkspaceGuestStoreCommit.ts`; the limit predicate is re-exported
 *     through the store for its specs.
 */

import { ApiError, isApiError } from "../../../api/client";

/** The server's cursor/revision conflict (`ExamWorkspaceParentsHandler._apply`). */
export function conflictError(): ApiError {
  return new ApiError({
    code: "CONFLICT",
    message: "Dokumentet har ändrats sedan det öppnades.",
    status: 409,
  });
}

/** The server's refusal of a write from a tab that does not hold the live edit lease. */
export function editLeaseHeldError(): ApiError {
  return new ApiError({
    code: "EDIT_LEASE_HELD",
    message: "Provet redigeras i en annan flik.",
    status: 409,
  });
}

/** The server's refusal of a document the save rules reject; carries the Swedish copy. */
export function refusalError(copy: string): ApiError {
  return new ApiError({ code: "VALIDATION_ERROR", message: copy, status: 422 });
}

/** The server's document-not-found (`_document_not_found`), for an unknown guest lineage. */
export function notFoundError(lineageId: string): ApiError {
  return new ApiError({
    code: "NOT_FOUND",
    message: "Provdokumentet finns inte.",
    status: 404,
    details: { lineage_id: lineageId },
  });
}

/** The server's outdated-format refusal, for a stored draft the browser cannot read. */
export function outdatedGuestDocumentError(): ApiError {
  return new ApiError({
    code: "DOCUMENT_SCHEMA_OUTDATED",
    message: "Native exam document uses an outdated schema version.",
    status: 422,
  });
}

/** The public routes' hourly guest limit arrives as a plain 429. */
export function isGuestLimitError(error: unknown): boolean {
  return isApiError(error) && error.status === 429;
}
