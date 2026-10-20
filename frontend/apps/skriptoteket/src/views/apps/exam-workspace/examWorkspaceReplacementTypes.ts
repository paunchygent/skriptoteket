/**
 * Exam workspace replacement contract (TASK-SKRIPT-40-04-14, R9-1).
 *
 * Domain purpose:
 *   The shared vocabulary of the gate-owned replacement coordinator: one
 *   immutable request object per intent (a route open names its lineage;
 *   Spara som names the captured source lineage and the requested name until
 *   its response supplies the new lineage; recovery names the retained
 *   source), the routed outcome, and the barrier and selection ports the
 *   coordinator's owner binds.
 *
 * Relationships:
 *   - Owned by `examWorkspaceReplacementCoordinator`, which stays the only
 *     replacement owner; the document open primitive reports the routed
 *     outcome through this contract.
 */

import type { ExamWorkspaceDocumentResponse } from "../../../api/examWorkspace";
import type { FenceToken, SyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceSaveAsOutcome } from "./useExamWorkspaceSave";

export type { ExamWorkspaceSaveAsOutcome };

/** A routed open's outcome: installed, superseded by a newer request, or failed while current. */
export type ExamWorkspaceRouteOpenOutcome = "installed" | "superseded" | "failed";

/** One immutable replacement request. Request-object identity tells Y1 from
 * Y2 when Z intervenes; lineage equality is not request identity. */
export type ExamWorkspaceReplacementIntent =
  | { readonly kind: "route"; readonly lineage: string }
  | { readonly kind: "saveAs"; readonly source: string; readonly name: string }
  | { readonly kind: "recover"; readonly source: string | null };

export type ExamWorkspaceReplacementRouteEntry = {
  kind: "route";
  intent: Extract<ExamWorkspaceReplacementIntent, { kind: "route" }>;
  resolve: (outcome: ExamWorkspaceRouteOpenOutcome) => void;
  promise: Promise<ExamWorkspaceRouteOpenOutcome>;
};

export type ExamWorkspaceReplacementSaveAsEntry = {
  kind: "saveAs";
  intent: Extract<ExamWorkspaceReplacementIntent, { kind: "saveAs" }>;
  resolve: (outcome: ExamWorkspaceSaveAsOutcome) => void;
  promise: Promise<ExamWorkspaceSaveAsOutcome>;
};

export type ExamWorkspaceReplacementRecoverEntry = {
  kind: "recover";
  intent: Extract<ExamWorkspaceReplacementIntent, { kind: "recover" }>;
};

export type ExamWorkspaceReplacementDesired =
  | ExamWorkspaceReplacementRouteEntry
  | ExamWorkspaceReplacementSaveAsEntry
  | ExamWorkspaceReplacementRecoverEntry;

export type ExamWorkspaceReplacementSelected =
  | ExamWorkspaceReplacementRouteEntry
  | ExamWorkspaceReplacementSaveAsEntry;

export type ExamWorkspaceReplacementDeps = {
  /** True once the owner is torn down: every submission ends at once. */
  isDisposed: () => boolean;
  /** The installed source: the exam lineage in front of the teacher, if any. */
  installedSource: () => string | null;
  /** True while the gate phase admits writes. */
  isEditing: () => boolean;
  /** The generation owner: selections mint and settle against it. */
  fence: SyncFence;
  /** Run the settle flush under the replacing lock. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** Retire the current generation: outstanding settles resolve `stale`. */
  retireGeneration: () => void;
  /** Capture the unconfirmed copy as the gate's kept record. */
  captureKept: () => void;
  /** Freeze attempt tracking into the unresolved pieces. */
  abandonAttempt: () => void;
  /** True while a current-generation store is in flight. */
  hasActiveStore: () => boolean;
  /** The working copy visibly differs from the saved exam. */
  isVisibleDirty: () => boolean;
  /** The only definition of confirmation: no active, unresolved, kept or net intent. */
  hasUnconfirmed: () => boolean;
  /** Store the latest edit now; true when the server's newest step holds it. */
  settleEdit: () => Promise<boolean>;
  /** Read and install the named document for the selection's token. */
  openRouteTarget: (lineageId: string, token: FenceToken) => Promise<ExamWorkspaceRouteOpenOutcome>;
  /** Install a replacement response (route read or copy) without deciding anything. */
  installReplacementDocument: (token: FenceToken, response: ExamWorkspaceDocumentResponse) => void;
  /** Adopt the selected lineage: gate lineage, loading phase and step-list load, without retiring. */
  adoptSelectedOpening: (lineageId: string) => void;
  /** Claim the edit lease for the selected lineage. */
  claimSelectedLease: (lineageId: string) => void;
  /** Start the copy POST; null when its guards refuse. Holds the copy busy until retired or settled. */
  beginCopy: (
    sourceLineageId: string,
    name: string,
  ) => Promise<ExamWorkspaceDocumentResponse> | null;
  /** Report a current route-open failure (the existing open copy). */
  notifyRouteFailed: () => void;
  /** Report a current copy failure (the existing Spara som copy). */
  notifyCopyFailed: () => void;
  /** Release the retired copy selection's busy hold at once. */
  releaseCopyBusy: () => void;
  /** Recover the retained source through the gate's ordinary fresh-load path. */
  recoverRetainedSource: () => void;
  /** Publish the address; a repeated value is a no-op. */
  projectAddress: (lineageId: string | null) => void;
  /** Resolve once no router navigation is in flight. */
  waitForRouterIdle: () => Promise<void>;
};
