/**
 * Exam workspace route-request pipeline (TASK-SKRIPT-40-04-14, R8).
 *
 * Domain purpose:
 *   One route-request pipeline for leaving the open exam: settle the latest
 *   edit, retire the generation under the request's token, and report the
 *   outcome the address acts on. Per-piece kept intent belongs with the
 *   history write boundary and the sync gate's kept record; route code owns
 *   neither merge bases nor confirmation.
 *
 * Relationships:
 *   - The sync gate owns the retire step through `requestRouteRetire`; the
 *     document owns the read through its token open; the address owns the
 *     target and the recovery call.
 */

import type { FenceToken } from "./examWorkspaceSyncFence";

/** A routed open's outcome: installed, superseded by a newer request, or failed while current. */
export type ExamWorkspaceRouteOpenOutcome = "installed" | "superseded" | "failed";

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
