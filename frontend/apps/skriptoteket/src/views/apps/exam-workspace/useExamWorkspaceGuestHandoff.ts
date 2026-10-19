/**
 * Exam workspace guest handoff after sign-in.
 *
 * Domain purpose:
 *   A guest's exam lives only in this browser until the guest signs in. The
 *   signed-in workspace host runs this once on mount: the stored draft is
 *   posted to Mina filer through the signed-in guest-drafts route, and only
 *   after that post succeeds is the posted browser snapshot cleared. The
 *   returned lineage id is the exam the view opens; null means there was
 *   nothing to hand off, or the handoff failed and the browser copy was kept.
 *
 * Relationships:
 *   - Reads the draft through `examWorkspaceGuestDraftStorage` and hands the
 *     newest (position) document with its import notes over through the
 *     teacher store's `importExamWorkspaceGuestDraft`, mirroring the guest
 *     export multipart shape (`draft_id`, `document`, `notes`, one
 *     `asset:<id>` part per declared picture).
 *   - The idempotency key is the snapshot cursor, not the draft: the server
 *     claims once per (user, key), so a later handoff of newer edits posts a
 *     new cursor and imports its own exam instead of returning the old
 *     snapshot.
 *   - After a successful post only the posted snapshot is cleared: a newer
 *     draft or newer edits (a new cursor) are kept untouched. A failed post
 *     keeps the browser copy and shows one failure toast; a failed clearIf
 *     after a successful post still hands the lineage back, because the
 *     server ledger makes a repeated post of the same snapshot a no-op.
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
  const snapshotCursor = stored.draft.cursor;
  const document = guestDocumentResponse(stored.draft).document;
  let response: ExamWorkspaceDocumentResponse;
  try {
    response = await deps.teacher.importExamWorkspaceGuestDraft(
      snapshotCursor,
      document,
      declaredAssets(document, stored.assets),
      stored.draft.notes,
    );
  } catch {
    useToast().failure(GUEST_HANDOFF_FAILURE_COPY);
    return null;
  }
  try {
    await deps.storage.clearIf(snapshotCursor);
  } catch {
    // The exam is already saved; the server ledger makes a repeated post of
    // the same snapshot a no-op. A newer draft (a new cursor) is kept by
    // clearIf itself, so it is never deleted here.
  }
  return response.summary.lineage_id;
}
