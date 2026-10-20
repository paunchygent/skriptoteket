/**
 * Exam workspace guest handoff after sign-in.
 *
 * Domain purpose:
 *   A guest's exam lives only in this browser until the guest signs in. The
 *   signed-in workspace host runs this once on mount: the stored draft is
 *   posted to Mina filer through the signed-in guest-drafts route, and only
 *   after that post succeeds is the posted browser snapshot cleared. One
 *   attempt returns one typed outcome: `handed_off` carries the new exam's
 *   lineage id; `none` means there was nothing to hand off; `rejected`
 *   carries the recorded reason and the stored draft; `transient` and
 *   `deferred` mean a later attempt may still succeed.
 *
 *   A permanent or vault-full rejection is recorded per draft cursor. While
 *   the record matches the stored draft's cursor, later calls return the
 *   rejection without posting, so a rejected draft is never posted again.
 *   A newer draft (a new cursor) makes the record stale and clears that
 *   cursor before posting. Every attempt runs inside one cross-tab lock and
 *   carries the controller's owner: a retired owner defers with no POST and
 *   no record or draft mutation. This module shows no toasts: a later
 *   controller unit owns all user messages.
 *
 * Relationships:
 *   - Reads the draft through `examWorkspaceGuestDraftStorage`, the
 *     rejection record through `examWorkspaceGuestHandoffRejection`, and
 *     hands the newest (position) document with its import notes over
 *     through the teacher store's `importExamWorkspaceGuestDraft`,
 *     mirroring the guest export multipart shape (`draft_id`, `document`,
 *     `notes`, one `asset:<id>` part per declared picture).
 *   - The idempotency key is the snapshot cursor, not the draft: the
 *     server claims once per (user, key), so a later handoff of newer edits
 *     posts a new cursor and imports its own exam instead of returning the
 *     old snapshot.
 *   - After a successful post only the posted snapshot is cleared: a newer
 *     draft or newer edits (a new cursor) are kept untouched. A failed post
 *     keeps the browser copy; the record and the outcome tell the caller
 *     what happened. A failed clearIf after a successful post still hands
 *     the lineage back, because the server ledger makes a repeated post of
 *     the same snapshot a no-op.
 */

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { AuthSession } from "../../../stores/auth";
import { classifyGuestHandoffFailure } from "./examWorkspaceGuestHandoffFailure";
import type { GuestHandoffRejectionStoragePort } from "./examWorkspaceGuestHandoffRejection";
import type { GuestHandoffLockPort } from "./examWorkspaceGuestHandoffLock";
import { guestDocumentResponse, type ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import type {
  ExamWorkspaceGuestDraftStoragePort,
  StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";

export type GuestHandoffTeacher = Pick<
  ExamWorkspaceTeacherServices,
  "importExamWorkspaceGuestDraft"
>;

export type GuestHandoffOutcome =
  | { kind: "none" }
  | { kind: "handed_off"; lineageId: string }
  | { kind: "rejected"; reason: "permanent" | "vault_full"; draft: ExamWorkspaceGuestDraft }
  | { kind: "transient" }
  | { kind: "deferred" };

export type GuestHandoffDeps = {
  storage: ExamWorkspaceGuestDraftStoragePort;
  teacher: GuestHandoffTeacher | null;
  rejections: GuestHandoffRejectionStoragePort;
  lock: GuestHandoffLockPort;
  owner: GuestHandoffOwner;
};

/**
 * The handoff owner's auth lifetime: the session captured when the
 * controller is created, plus whether that owner is still live (not disposed
 * and still the current session). Every attempt re-checks it after each
 * await and returns `deferred` once it is retired, with no POST and no
 * record or draft mutation.
 */
export type GuestHandoffOwner = {
  session: AuthSession;
  isLive(): boolean;
};

export type RunGuestHandoffOptions = {
  /**
   * A draft cursor holding a vault-full notice. The recorded rejection is
   * bypassed only when the record is `vault_full` for this same cursor and
   * the stored draft still has it; any other record is honoured.
   */
  retryVaultFullOf?: string;
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
 * Hand the stored browser draft to Mina filer. Makes at most one POST and
 * returns the outcome; the browser draft is kept in every failure case.
 *
 * The whole attempt runs inside the cross-tab handoff lock: the draft and
 * the record are re-read after admission, so a second tab observes the first
 * tab's permanent outcome instead of posting again. A failed attempt writes
 * its record only when the stored draft still has the posted cursor; success
 * and removal clear only their own cursor's record. Once the POST has
 * resolved, a success always clears the posted snapshot's slot and its own
 * record first, and only then defers when the owner has retired.
 */
export async function runGuestHandoff(
  deps: GuestHandoffDeps,
  options?: RunGuestHandoffOptions,
): Promise<GuestHandoffOutcome> {
  return await deps.lock.run(async () => {
    if (!deps.owner.isLive()) {
      return { kind: "deferred" };
    }
    let stored: Awaited<ReturnType<GuestHandoffDeps["storage"]["load"]>>;
    try {
      stored = await deps.storage.load();
    } catch {
      return { kind: "none" };
    }
    if (!deps.owner.isLive()) {
      return { kind: "deferred" };
    }
    if (stored === null || deps.teacher === null) {
      return { kind: "none" };
    }
    const snapshotCursor = stored.draft.cursor;

    const recorded = deps.rejections.read();
    if (recorded !== null && recorded.cursor !== snapshotCursor) {
      deps.rejections.clearIf(recorded.cursor);
    } else if (
      recorded !== null &&
      recorded.cursor === snapshotCursor &&
      (options?.retryVaultFullOf !== snapshotCursor || recorded.reason !== "vault_full")
    ) {
      return { kind: "rejected", draft: stored.draft, reason: recorded.reason };
    }

    let document: NativeExamDocument;
    try {
      document = guestDocumentResponse(stored.draft).document;
    } catch {
      const rejection = { cursor: snapshotCursor, reason: "permanent" as const };
      deps.rejections.write(rejection);
      return { draft: stored.draft, kind: "rejected", reason: "permanent" };
    }

    const missingBytes = document.assets.some(
      (asset) => stored.assets[asset.asset_id] === undefined,
    );
    if (missingBytes) {
      const rejection = { cursor: snapshotCursor, reason: "permanent" as const };
      deps.rejections.write(rejection);
      return { draft: stored.draft, kind: "rejected", reason: "permanent" };
    }

    let response: ExamWorkspaceDocumentResponse;
    try {
      response = await deps.teacher.importExamWorkspaceGuestDraft(
        snapshotCursor,
        document,
        declaredAssets(document, stored.assets),
        stored.draft.notes,
        deps.owner.session,
      );
    } catch (error) {
      const kind = classifyGuestHandoffFailure(error);
      if (kind === "permanent" || kind === "vault_full") {
        if (!deps.owner.isLive()) {
          return { kind: "deferred" };
        }
        let current: StoredGuestDraft | null;
        try {
          current = await deps.storage.load();
        } catch {
          return { kind: "none" };
        }
        if (!deps.owner.isLive()) {
          return { kind: "deferred" };
        }
        if (current?.draft.cursor !== snapshotCursor) {
          return { kind: "none" };
        }
        deps.rejections.write({ cursor: snapshotCursor, reason: kind });
        return { draft: stored.draft, kind: "rejected", reason: kind };
      }
      if (kind === "deferred") {
        return { kind: "deferred" };
      }
      return { kind: "transient" };
    }
    // The POST resolved: the posted snapshot is saved, so its slot and its
    // own record are always cleared, even when the owner retired while the
    // POST was in flight. Both are owned by the cursor that was just saved,
    // so a newer draft (a new cursor) is never touched. Only then does a
    // retired owner defer instead of handing off.
    try {
      await deps.storage.clearIf(snapshotCursor);
    } catch {
      // The exam is already saved; the server ledger makes a repeated post of
      // the same snapshot a no-op. A newer draft (a new cursor) is kept by
      // clearIf itself, so it is never deleted here.
    }
    deps.rejections.clearIf(snapshotCursor);
    if (!deps.owner.isLive()) {
      return { kind: "deferred" };
    }
    return { kind: "handed_off", lineageId: response.summary.lineage_id };
  });
}
