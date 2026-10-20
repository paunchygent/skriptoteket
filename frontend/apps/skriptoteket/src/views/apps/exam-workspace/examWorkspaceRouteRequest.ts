/**
 * Exam workspace route-request pipeline (TASK-SKRIPT-40-04-14, R8).
 *
 * Domain purpose:
 *   One route-request pipeline for leaving the open exam: settle the latest
 *   edit, retire the generation under the request's token, read the requested
 *   exam under that token, and report the outcome the address acts on. A kept
 *   edit exists whenever the desired copy is unconfirmed: the working copy
 *   differs from the last confirmed store, or a store is in flight whose
 *   answer is unknown. The kept edit records the confirmed base, the
 *   in-flight document (or null) and the edited working copy. The fresh load
 *   merges from the in-flight document when the server's fresh copy holds the
 *   same content (the store committed), and from the confirmed base
 *   otherwise.
 *
 * Relationships:
 *   - The sync gate owns the retire step through `requestRouteRetire` and the
 *     kept capture through the helpers; the document owns the read through
 *     its token open; the address owns the target and the recovery call.
 */

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { FenceToken } from "./examWorkspaceSyncFence";
import { sameContent } from "./useExamWorkspaceHistoryStore";

/** A routed open's outcome: installed, superseded by a newer request, or failed while current. */
export type ExamWorkspaceRouteOpenOutcome = "installed" | "superseded" | "failed";

/** The kept edit: the confirmed base, the in-flight document (or null) and the edited working copy. */
export type ExamWorkspaceRouteKeptEdit = {
  /** The step document the desired copy stands on. */
  base: NativeExamDocument;
  /** What the in-flight store sent while its answer was unknown, or null when no store was in flight. */
  inflight: NativeExamDocument | null;
  /** The working copy in front of the teacher. */
  edited: NativeExamDocument;
};

/** A kept edit exists while the working copy is unconfirmed or a store answer is unknown. */
export function shouldCaptureKeptEdit(hasPendingEdit: boolean, inflight: NativeExamDocument | null): boolean {
  return hasPendingEdit || inflight !== null;
}

/** The merge base for a kept edit against the server's fresh copy. */
export function pickKeptMergeBase(kept: ExamWorkspaceRouteKeptEdit, fresh: NativeExamDocument): NativeExamDocument {
  if (kept.inflight !== null && sameContent(fresh, kept.inflight)) {
    return kept.inflight;
  }
  return kept.base;
}

export type ExamWorkspaceRouteRetireDeps = {
  /** True while the gate phase admits writes. */
  isEditing: () => boolean;
  /** True once the gate is torn down. */
  isDisposed: () => boolean;
  /** Run the settle flush under the replacing lock, so no keystroke lands between its confirmation and the retire. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** Store the latest edit now; true when the server's newest step holds it. */
  settleEdit: () => Promise<boolean>;
  /** Retire the current generation. */
  retire: () => void;
  /** Mint the request's token in the fresh generation. */
  begin: () => FenceToken;
};

/**
 * Settle before retire: while editing, store the latest edit first, and only
 * when the store lands retire in the same continuation and hand back the
 * request's token. When the store does not land, hand back null and retire
 * nothing, so the address restores and opens nothing. Outside editing there
 * is nothing to settle: retire at once.
 */
export async function requestRouteRetire(deps: ExamWorkspaceRouteRetireDeps): Promise<FenceToken | null> {
  if (deps.isDisposed()) {
    return null;
  }
  if (deps.isEditing()) {
    const stored = await deps.replaceCopy(() => deps.settleEdit());
    if (!stored || deps.isDisposed()) {
      return null;
    }
  }
  deps.retire();
  return deps.begin();
}
