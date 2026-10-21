/**
 * Guest exam workspace slot starts.
 *
 * Domain purpose:
 *   Start a new guest exam in the one browser slot: a blank exam (Nytt prov)
 *   or a QTI .zip read through the public parse route. Either start replaces
 *   the whole slot, which deletes the retained draft, its history and its
 *   picture bytes, so every start writes through the conditional slot write
 *   and never over a newer draft another tab stored first.
 *
 * Relationships:
 *   - Built by `examWorkspaceGuestStore.ts`, which supplies the limit-wrapped
 *     public API, its edit-lease check and its conditional `persist`.
 *   - Nytt prov arrives from the replacement coordinator with a
 *     `GuestSlotAdmission`; the QTI start is called by the conversion import
 *     intake and carries no replacement authority.
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
  /** The guest store's conditional slot write; `admit` is checked inside it. */
  persist: (
    expectedCursor: string | null,
    stored: StoredGuestDraft,
    admit?: () => boolean,
  ) => Promise<void>;
};

export function createGuestSlotStarts(deps: GuestSlotStartDeps) {
  /**
   * Replace the whole browser slot with the draft `produce` builds. The slot
   * cursor is captured before awaiting `produce`, so a concurrent tab that
   * commits while the public route is in flight owns the slot afterwards and
   * this write reports the established 409 instead of overwriting its draft.
   */
  async function replaceSlotWith(produce: () => Promise<StoredGuestDraft>): Promise<string> {
    const current = await deps.storage.load();
    const expectedCursor = current?.draft.cursor ?? null;
    const next = await produce();
    await deps.persist(expectedCursor, next);
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
   * The write is admitted only under the creation's live authority: a tab
   * that took over the edit lease refuses it like any other write, and
   * `admission.isLive` is checked inside the atomic slot write itself. A
   * creation retired while its blank was in flight, including after a lease
   * handover whose new owner has stored nothing yet, never replaces the
   * draft; suppressing only the late response would come after the
   * destructive write.
   */
  async function startBlank(
    expectedCursor: string | null,
    admission: GuestSlotAdmission,
  ): Promise<string> {
    const response = await deps.api.createPublicExamWorkspaceBlank();
    const draft = newGuestDraft(response.document, deps.ids, []);
    await deps.requireEditLease(admission.tabId);
    await deps.persist(expectedCursor, { assets: {}, draft }, admission.isLive);
    return draft.lineage_id;
  }

  /**
   * Start a guest exam from a QTI .zip through the public parse route: the
   * returned document becomes the draft and its picture bytes stay beside
   * it in the browser. A concurrent tab's newer draft is kept, like a lost
   * blank start, and a limit hit reports through `onLimit`.
   */
  async function startFromQti(file: File, courseKey: string | null): Promise<string> {
    return await replaceSlotWith(async () => {
      const response = await deps.api.importPublicExamWorkspaceQti(file, courseKey);
      const draft = newGuestDraft(response.document, deps.ids, response.notes);
      return { assets: response.assets, draft };
    });
  }

  return { startBlank, startFromQti };
}
