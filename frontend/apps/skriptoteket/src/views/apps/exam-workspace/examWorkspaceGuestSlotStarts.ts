/**
 * Guest exam workspace slot starts.
 *
 * Domain purpose:
 *   Start a new guest exam in the one browser slot: a blank exam (Nytt prov)
 *   or a QTI .zip read through the public parse route. Either start replaces
 *   the whole slot, which deletes the retained draft, its history and its
 *   picture bytes, so every start writes through the atomic whole-slot
 *   write: never over a newer draft another tab stored first, never while
 *   another tab holds a live edit lease, and never after the starting
 *   operation was retired.
 *
 * Relationships:
 *   - Built by `examWorkspaceGuestStore.ts`, which supplies the limit-wrapped
 *     public API, its edit-lease check and its whole-slot `replaceSlot`.
 *   - Both starts carry a `GuestSlotAdmission`: Nytt prov from the
 *     replacement coordinator, the QTI start from the conversion import
 *     intake, bound to that import's own lifecycle.
 */

import { newGuestDraft, type ExamWorkspaceGuestDraftIdSource } from "./examWorkspaceGuestDraft";
import type {
  ExamWorkspaceGuestDraftStoragePort,
  StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import type { GuestPublicApi } from "./examWorkspaceGuestLimitApi";
import type { GuestSlotAdmission } from "./examWorkspaceStore";

export type GuestSlotStartDeps = {
  api: Pick<GuestPublicApi, "createPublicExamWorkspaceBlank" | "importPublicExamWorkspaceQti">;
  ids: ExamWorkspaceGuestDraftIdSource;
  storage: ExamWorkspaceGuestDraftStoragePort;
  /** Refuse a write while another tab holds a live edit lease (`EDIT_LEASE_HELD`). */
  requireEditLease: (tabId: string) => Promise<void>;
  /**
   * The guest store's whole-slot write: the cursor, the edit lease and
   * `admission.isLive` are decided inside one atomic step with the write.
   */
  replaceSlot: (
    expectedCursor: string | null,
    stored: StoredGuestDraft,
    admission: GuestSlotAdmission,
  ) => Promise<void>;
};

export function createGuestSlotStarts(deps: GuestSlotStartDeps) {
  /**
   * Replace the whole browser slot with the draft `produce` builds. The slot
   * cursor is captured before awaiting `produce`, so a concurrent tab that
   * commits while the public route is in flight owns the slot afterwards and
   * this write reports the established 409 instead of overwriting its draft.
   */
  async function replaceSlotWith(
    produce: () => Promise<StoredGuestDraft>,
    admission: GuestSlotAdmission,
  ): Promise<string> {
    const current = await deps.storage.load();
    const expectedCursor = current?.draft.cursor ?? null;
    const next = await produce();
    await deps.replaceSlot(expectedCursor, next, admission);
    return next.draft.lineage_id;
  }

  /**
   * Start a fresh blank exam through the public route and store it. The
   * D9 check's cursor arrives as `expectedCursor` and passes straight to
   * the conditional write: no fresh load re-reads the slot, so a stale or
   * read-only view of an empty exam can never replace a newer
   * content-bearing draft another tab stored after the check. A concurrent
   * tab's newer draft is kept and reported as the established conflict.
   *
   * The write is admitted only under the creation's live authority. The
   * early lease check refuses at once while another tab holds the lease;
   * the deciding check runs inside the atomic slot write, with the cursor
   * and `admission.isLive`, so a tab that takes the lease after the early
   * check and before the write keeps the slot even before this tab sees its
   * loss. A creation retired while its blank was in flight, including after
   * a lease handover whose new owner has stored nothing yet, never replaces
   * the draft; suppressing only the late response would come after the
   * destructive write.
   */
  async function startBlank(
    expectedCursor: string | null,
    admission: GuestSlotAdmission,
  ): Promise<string> {
    const response = await deps.api.createPublicExamWorkspaceBlank();
    const draft = newGuestDraft(response.document, deps.ids, []);
    await deps.requireEditLease(admission.tabId);
    await deps.replaceSlot(expectedCursor, { assets: {}, draft }, admission);
    return draft.lineage_id;
  }

  /**
   * Start a guest exam from a QTI .zip through the public parse route: the
   * returned document becomes the draft and its picture bytes stay beside
   * it in the browser. A concurrent tab's newer draft is kept, like a lost
   * blank start, and a limit hit reports through `onLimit`. A late parse
   * never replaces the slot once `admission.isLive` turned false (the
   * import was retired or its workspace disposed) or another tab holds a
   * live edit lease: both are decided inside the atomic slot write.
   */
  async function startFromQti(
    file: File,
    courseKey: string | null,
    admission: GuestSlotAdmission,
  ): Promise<string> {
    return await replaceSlotWith(async () => {
      const response = await deps.api.importPublicExamWorkspaceQti(file, courseKey);
      const draft = newGuestDraft(response.document, deps.ids, response.notes);
      return { assets: response.assets, draft };
    }, admission);
  }

  return { startBlank, startFromQti };
}
