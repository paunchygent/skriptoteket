/**
 * Guest exam workspace store commit machinery.
 *
 * Domain purpose:
 *   The conditional write behind every guest mutation: load the browser
 *   draft for a lineage, run one server command against the editor's
 *   document, and commit the returned document as one new undo step after
 *   the current position, exactly as the server's commands do. The step also
 *   updates the saved draft in the same write, as the server's step store
 *   overwrites the exam file. The snapshot
 *   cursor is captured before the network call and the write commits only
 *   when that snapshot still owns the slot; a delayed command that lands
 *   after another tab's write reports the conflict and discards the network
 *   result instead of overwriting the newer draft.
 *
 * Relationships:
 *   - Reports the server-shaped refusals of
 *     `examWorkspaceGuestStoreErrors.ts` so the workspace UI cannot tell a
 *     browser refusal from the server one it mirrors.
 *   - Pure transition reuse from `examWorkspaceGuestDraft.ts`, persisted
 *     through the `examWorkspaceGuestDraftStorage.ts` port; the object-URL
 *     map stays in `examWorkspaceGuestStore.ts`, notified via `onStored`.
 *   - Consumed by `examWorkspaceGuestStore.ts` for the structural commands;
 *     the undo-step and position-move paths share `loadGuestStored`,
 *     `persistGuestStored` and `retainDeclaredAssets` directly, and the slot
 *     starts write through `replaceGuestSlot`.
 */

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import {
  guestDocumentResponse,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import type {
  ExamWorkspaceGuestDraftStoragePort,
  StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import {
  conflictError,
  editLeaseHeldError,
  notFoundError,
  refusalError,
} from "./examWorkspaceGuestStoreErrors";
import type { GuestSlotAdmission } from "./examWorkspaceStore";

export type PublicCommandResult = {
  document: NativeExamDocument;
  export_blockers: ExamWorkspaceDocumentResponse["export_blockers"];
};

/** The pictures a retained snapshot or the saved copy still declares. */
function declaredAssetIds(draft: ExamWorkspaceGuestDraft): Set<string> {
  const ids = new Set<string>();
  for (const step of [draft.baseline, ...draft.steps]) {
    for (const asset of step.document.assets) {
      ids.add(asset.asset_id);
    }
  }
  for (const asset of draft.saved_document.assets) {
    ids.add(asset.asset_id);
  }
  return ids;
}

/** Keep only the stored picture bytes whose id a retained snapshot or the saved copy declares. */
export function retainDeclaredAssets(
  stored: StoredGuestDraft,
  draft: ExamWorkspaceGuestDraft,
): Record<string, Blob> {
  const declared = declaredAssetIds(draft);
  const kept: Record<string, Blob> = {};
  for (const [assetId, blob] of Object.entries(stored.assets)) {
    if (declared.has(assetId)) {
      kept[assetId] = blob;
    }
  }
  return kept;
}

/** Load the browser draft for `lineageId`, or report the server's 404. */
export async function loadGuestStored(
  storage: ExamWorkspaceGuestDraftStoragePort,
  lineageId: string,
): Promise<StoredGuestDraft> {
  const stored = await storage.load();
  if (!stored || stored.draft.lineage_id !== lineageId) {
    throw notFoundError(lineageId);
  }
  return stored;
}

/**
 * Store `next` only when `expectedCursor` still owns the slot; a concurrent
 * tab's newer draft reports the server's 409. Notifies `onStored` once the
 * write commits so the caller can point its object URLs at the new bytes.
 */
export async function persistGuestStored(
  storage: ExamWorkspaceGuestDraftStoragePort,
  expectedCursor: string | null,
  next: StoredGuestDraft,
  onStored: (stored: StoredGuestDraft) => void,
): Promise<void> {
  const written = await storage.replaceIf(expectedCursor, next);
  if (!written) {
    throw conflictError();
  }
  onStored(next);
}

/**
 * Replace the whole slot with a new exam under `admission` (see
 * `replaceSlotIf`): a stale cursor or a retired writer reports the server's
 * 409 conflict, and another tab's live edit lease reports the server's
 * `EDIT_LEASE_HELD` 409. Notifies `onStored` once the write commits.
 */
export async function replaceGuestSlot(
  storage: ExamWorkspaceGuestDraftStoragePort,
  expectedCursor: string | null,
  next: StoredGuestDraft,
  admission: GuestSlotAdmission,
  onStored: (stored: StoredGuestDraft) => void,
): Promise<void> {
  const outcome = await storage.replaceSlotIf(expectedCursor, next, admission);
  if (outcome === "lease-held") {
    throw editLeaseHeldError();
  }
  if (outcome === "conflict") {
    throw conflictError();
  }
  onStored(next);
}

export type CommitGuestCommandOptions<Result extends PublicCommandResult> = {
  storage: ExamWorkspaceGuestDraftStoragePort;
  ids: ExamWorkspaceGuestDraftIdSource;
  lineageId: string;
  /** Check the draft exactly as the server checks it; a false return is its 409. */
  guard: (draft: ExamWorkspaceGuestDraft) => boolean;
  run: (document: NativeExamDocument) => Promise<Result>;
  onStored: (stored: StoredGuestDraft) => void;
  /**
   * Refuse a write from a tab that does not hold a live lease, after the
   * cursor guard: the server reports a stale cursor as its ordinary conflict
   * first, and the lease only after.
   */
  checkLease: () => Promise<void>;
};

/**
 * Run one server command against the editor's document and commit the
 * returned document as one new undo step after the current position.
 */
export async function commitGuestCommand<Result extends PublicCommandResult>(
  options: CommitGuestCommandOptions<Result>,
): Promise<{ result: Result; draft: ExamWorkspaceGuestDraft }> {
  const stored = await loadGuestStored(options.storage, options.lineageId);
  if (!options.guard(stored.draft)) {
    throw conflictError();
  }
  await options.checkLease();
  const expectedCursor = stored.draft.cursor;
  const current = guestDocumentResponse(stored.draft).document;
  const result = await options.run(current);
  const outcome = storeGuestUndoStep(
    stored.draft,
    { afterStepId: null, document: result.document, expectedCursor },
    options.ids,
  );
  if (outcome.kind === "conflict") {
    throw conflictError();
  }
  if (outcome.kind === "refused") {
    throw refusalError(outcome.copy);
  }
  await persistGuestStored(
    options.storage,
    expectedCursor,
    {
      assets: retainDeclaredAssets(stored, outcome.draft),
      draft: outcome.draft,
    },
    options.onStored,
  );
  return { draft: outcome.draft, result };
}
