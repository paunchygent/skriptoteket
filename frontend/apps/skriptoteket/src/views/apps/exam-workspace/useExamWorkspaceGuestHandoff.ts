/**
 * Exam workspace guest handoff after sign-in.
 *
 * Domain purpose:
 *   A guest's exam lives only in this browser until the guest signs in. The
 *   signed-in workspace host runs this once on mount: the stored draft is
 *   posted to Mina filer through the signed-in guest-drafts route, and only
 *   after that post succeeds is the browser copy cleared. The returned
 *   lineage id is the exam the view opens; null means there was nothing to
 *   hand off, or the handoff failed and the browser copy was kept.
 *
 * Relationships:
 *   - Reads the draft through `examWorkspaceGuestDraftStorage` and hands the
 *     newest (position) document over through the teacher store's
 *     `importExamWorkspaceGuestDraft`, mirroring the guest export multipart
 *     shape (`draft_id`, `document`, one `asset:<id>` part per declared
 *     picture).
 *   - A failed post keeps the browser copy and shows one failure toast; a
 *     failed `clear()` after a successful post still hands the lineage back,
 *     because the server ledger makes the next attempt a no-op.
 */

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { guestDocumentResponse } from "./examWorkspaceGuestDraft";
import type { ExamWorkspaceGuestDraftStoragePort } from "./examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";

export const GUEST_HANDOFF_FAILURE_COPY =
  "Det gick inte att spara provet från webbläsaren i Mina filer. Det finns kvar i webbläsaren, försök igen genom att ladda om sidan.";

export type GuestHandoffTeacher = Pick<
  ExamWorkspaceTeacherServices,
  "importExamWorkspaceGuestDraft"
>;

export type GuestHandoffDeps = {
  storage: ExamWorkspaceGuestDraftStoragePort;
  teacher: GuestHandoffTeacher | null;
};

/** Only the pictures the handed-off document declares travel with it. */
function declaredAssets(
  document: NativeExamDocument,
  stored: Record<string, Blob>,
): Record<string, Blob> {
  const declared: Record<string, Blob> = {};
  for (const asset of document.assets) {
    const blob = stored[asset.asset_id];
    if (blob) {
      declared[asset.asset_id] = blob;
    }
  }
  return declared;
}

/**
 * Hand the stored browser draft to Mina filer. Returns the new exam's
 * lineage id, or null when there was no draft or the post failed.
 */
export async function runGuestHandoff(deps: GuestHandoffDeps): Promise<string | null> {
  let stored: Awaited<ReturnType<GuestHandoffDeps["storage"]["load"]>>;
  try {
    stored = await deps.storage.load();
  } catch {
    return null;
  }
  if (stored === null || deps.teacher === null) {
    return null;
  }
  const document = guestDocumentResponse(stored.draft).document;
  let response: ExamWorkspaceDocumentResponse;
  try {
    response = await deps.teacher.importExamWorkspaceGuestDraft(
      stored.draft.draft_id,
      document,
      declaredAssets(document, stored.assets),
    );
  } catch {
    useToast().failure(GUEST_HANDOFF_FAILURE_COPY);
    return null;
  }
  try {
    await deps.storage.clear();
  } catch {
    // The exam is already saved; the server ledger makes a repeated post a no-op.
  }
  return response.summary.lineage_id;
}
