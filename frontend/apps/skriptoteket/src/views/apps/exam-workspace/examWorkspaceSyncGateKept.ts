/**
 * Exam workspace sync gate kept record (TASK-SKRIPT-40-04-14, R9-2).
 *
 * Domain purpose:
 *   Own the gate's kept unconfirmed work: the exam it belongs to, an
 *   immutable snapshot of the desired copy D, and the owned piece set P (the
 *   confirmed-against-desired diff plus published, active and already-kept
 *   pieces). Capture runs before any retirement; a second loss recaptures from
 *   the latest D while retaining the kept keys, so a rebase never drops
 *   ownership a store has not confirmed. A real current store trims the kept
 *   pieces to the still-outstanding ones and clears them only when no kept
 *   piece differs and no published piece stays unresolved; a generation-only
 *   acknowledgement for an older snapshot never clears kept work that snapshot
 *   did not cover.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceSyncGate`, which stays the semantic owner;
 *     the recovery commit and the history's confirmation predicate read this
 *     record through the gate.
 */

import { computed, shallowRef } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { diffPieces } from "./examWorkspaceEditPieces";
import type { FenceToken, SyncFence } from "./examWorkspaceSyncFence";

/** The kept unconfirmed work: the exam it belongs to, an immutable snapshot
 * of the desired copy D, and the owned piece set P (`diffPieces` of the
 * confirmed copy against D, plus published, active and already-kept pieces).
 */
export type ExamWorkspaceSyncGateKeptEdit = {
  /** The exam lineage the desired snapshot belongs to. */
  lineage: string;
  /** The working copy in front of the teacher, kept until a store confirms it. */
  desired: NativeExamDocument;
  /** The owned pieces: desired wins each of them in the recovery commit. */
  pieces: Set<string>;
};

export type ExamWorkspaceSyncGateKeptDeps = {
  /** The exam lineage the gate stands on; null before the first open. */
  lineage: () => string | null;
  /** True once the gate is torn down. */
  isDisposed: () => boolean;
  /** The generation owner; only a current token trims the record. */
  fence: SyncFence;
  /** The confirmed copy C the write boundary stands on, if any. */
  confirmedCopy: () => NativeExamDocument | null;
  /** The desired copy D in front of the teacher, if any. */
  desiredCopy: () => NativeExamDocument | null;
  /** The unresolved published pieces: U plus the active attempt's pieces. */
  publishedPieces: () => Set<string>;
  /** Drop structural snapshots owed from a copy the retirement dropped. */
  dropOwedSnapshots: () => void;
};

/**
 * An immutable snapshot of a document. The working copy is a deep reactive
 * value, which `structuredClone` rejects, so the snapshot goes through JSON;
 * documents are plain server JSON.
 */
function snapshotDocument(document: NativeExamDocument): NativeExamDocument {
  const snapshot: NativeExamDocument = JSON.parse(JSON.stringify(document));
  return snapshot;
}

export function createSyncGateKept(deps: ExamWorkspaceSyncGateKeptDeps) {
  const kept = shallowRef<ExamWorkspaceSyncGateKeptEdit | null>(null);

  /**
   * Capture the unconfirmed copy as the kept record before any retirement.
   * With an empty P there is no kept work.
   */
  function captureKeptEdit(): void {
    const confirmed = deps.confirmedCopy();
    const desired = deps.desiredCopy();
    const lineageId = deps.lineage();
    if (confirmed === null || desired === null || lineageId === null) {
      deps.dropOwedSnapshots();
      return;
    }
    const pieces = new Set<string>([
      ...diffPieces(confirmed, desired),
      ...deps.publishedPieces(),
      ...(kept.value !== null && kept.value.lineage === lineageId ? kept.value.pieces : []),
    ]);
    if (pieces.size === 0) {
      kept.value = null;
    } else {
      kept.value = { desired: snapshotDocument(desired), lineage: lineageId, pieces };
    }
    deps.dropOwedSnapshots();
  }

  /**
   * A store confirmed this document under the current token. Keep the kept
   * pieces until a real current store confirms them: recompute the still
   * outstanding pieces against the latest copies, and clear only when no
   * kept piece differs and no published piece stays unresolved.
   */
  function noteStoredBy(token: FenceToken): void {
    if (deps.isDisposed() || !deps.fence.isCurrent(token)) {
      return;
    }
    const pendingKept = kept.value;
    if (pendingKept === null || pendingKept.lineage !== deps.lineage()) {
      return;
    }
    const confirmed = deps.confirmedCopy();
    const desired = deps.desiredCopy();
    if (confirmed === null || desired === null) {
      return;
    }
    const outstanding = [...pendingKept.pieces].filter(
      (piece) =>
        diffPieces(confirmed, desired).has(piece) || deps.publishedPieces().has(piece),
    );
    if (outstanding.length === 0) {
      kept.value = null;
    } else {
      kept.value = {
        desired: snapshotDocument(desired),
        lineage: pendingKept.lineage,
        pieces: new Set(outstanding),
      };
    }
  }

  /** The gate holds unconfirmed work; the save status never reports `Sparat` while it does. */
  const hasKeptEdit = computed(() => kept.value !== null);

  return { captureKeptEdit, hasKeptEdit, kept, noteStoredBy };
}
