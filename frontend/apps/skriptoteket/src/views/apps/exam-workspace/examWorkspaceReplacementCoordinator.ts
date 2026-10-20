/**
 * Exam workspace replacement coordinator (TASK-SKRIPT-40-04-14, R9-1).
 *
 * Domain purpose:
 *   One gate-owned owner for every document replacement: it holds one desired
 *   intent (an immutable request object, or none), the stage (idle, settling
 *   the source behind one shared barrier, or running the selected
 *   replacement) and the selected replacement context
 *   (the selected intent with its token from the existing fence). The
 *   installed source is read from the exam in front of the teacher, never
 *   cached: external opens land there too. A route-open
 *   intent carries its lineage; Spara som carries the captured source lineage
 *   and the requested name until its response supplies the new lineage.
 *   Request-object identity tells Y1 from Y2; lineage equality never does.
 *   Replacing the slot resolves its former caller as superseded at once;
 *   callers never wait in a queue.
 *
 *   The latest accepted intent wins, recorded synchronously before any await.
 *   An ordinary address request from an otherwise idle source keeps the
 *   visible-dirty refusal; once a departure settles, later requests replace
 *   the desired intent without another settle or dirty check. Settlement runs
 *   under the existing `replaceCopy` lock with the existing settle flush; on
 *   success, inside the still-held lock, the source token must be current, the
 *   scope live and the history free of unconfirmed intent then, in one
 *   synchronous step without an await, the latest desired intent is read, the
 *   source generation retired, the replacement token minted from the same
 *   fence and the selected context installed, and only then is the lock
 *   released. A failed or refused settle opens and retires nothing for that
 *   departure: the currently desired departure ends, the source and its work
 *   stay, and the source address is projected. An old request's null result
 *   cleans up nothing; a settle completion after lease loss or pagehide moved
 *   the generation is stale and does nothing.
 *
 *   After selection every result is admitted only while its intent is still
 *   the desired intent and its token is current in the one fence. A newer
 *   target during a selected read or copy retires that selection through the
 *   fence and selects the newer target; waits settle through the fence so a
 *   retired read never holds a newer target. A failed selected target recovers
 *   the retained source through the gate's ordinary fresh-load path in a new
 *   current context; a newer intent supersedes that recovery like any other
 *   replacement. A hung current store holds the switch (the L12 residual):
 *   later targets replace the slot and none opens early.
 *
 * Relationships:
 *   - Instantiated by `useExamWorkspaceSyncGate`, which stays the semantic
 *     owner; the gate binds the barrier ports from its own state and the
 *     selection ports from the editing session (document read and install,
 *     lease claim, copy transport, address projection).
 *   - The address is an adapter over this coordinator: it parses address
 *     requests and submits them synchronously, and the coordinator alone
 *     publishes the address for its current intent or failure recovery.
 */

import type { FenceToken } from "./examWorkspaceSyncFence";
import { isCopyNameTaken } from "./useExamWorkspaceSave";
import type {
  ExamWorkspaceReplacementDeps,
  ExamWorkspaceReplacementDesired,
  ExamWorkspaceReplacementRouteEntry,
  ExamWorkspaceReplacementSaveAsEntry,
  ExamWorkspaceReplacementSelected,
  ExamWorkspaceRouteOpenOutcome,
  ExamWorkspaceSaveAsOutcome,
} from "./examWorkspaceReplacementTypes";



export function createReplacementCoordinator(deps: ExamWorkspaceReplacementDeps) {
  /** The single latest-intent slot: one immutable request object, or none. */
  let desired: ExamWorkspaceReplacementDesired | null = null;
  /** Idle, settling the source behind one shared barrier, or running the selected replacement. */
  let stage: "idle" | "settling" | "running" = "idle";
  /** The selected replacement context: the selected entry with its fence token. */
  let selected: { entry: ExamWorkspaceReplacementSelected; token: FenceToken } | null = null;

  /** The address the coordinator stands behind: the desired target while a
   * departure runs, else the installed source. A projection echo matching
   * this value is idempotent; anything else becomes a new intent. */
  function currentAddress(): string | null {
    const entry = desired;
    if (entry === null) {
      return deps.installedSource();
    }
    const intent = entry.intent;
    return intent.kind === "route" ? intent.lineage : intent.source;
  }

  /** Replace the slot: its former caller resolves at once and never waits. */
  function replaceDesired(): void {
    const current = desired;
    desired = null;
    if (current === null) {
      return;
    }
    switch (current.kind) {
      case "route":
        current.resolve("superseded");
        break;
      case "saveAs":
        // Spara som knows no superseded outcome: an obsolete copy never runs.
        current.resolve("failed");
        break;
      case "recover":
        break;
    }
  }

  /** Release the running selection's busy hold; a retired read stops blocking
   * reactively through the fence, the retired copy through this call. */
  function retireSelected(): void {
    const current = selected;
    selected = null;
    if (current !== null && current.entry.kind === "saveAs") {
      deps.releaseCopyBusy();
    }
  }

  /**
   * In one synchronous step read the latest desired intent, retire the source
   * generation, mint the replacement token from the same fence and install
   * the selected context. There is no await between choosing the winner and
   * establishing this context.
   */
  function selectDesired(): void {
    const entry = desired;
    if (entry === null || entry.kind === "recover") {
      return;
    }
    retireSelected();
    deps.retireGeneration();
    const token = deps.fence.begin();
    selected = { entry, token };
    stage = "running";
    if (entry.kind === "route") {
      deps.projectAddress(entry.intent.lineage);
    }
  }

  /** True while the entry still owns the selected context: the selection holds
   * it, its token is current in the one fence, and the scope is live. Every
   * replacement result checks this before touching anything. */
  function isSelected(entry: ExamWorkspaceReplacementSelected, token: FenceToken): boolean {
    return (
      !deps.isDisposed() &&
      selected !== null &&
      selected.entry === entry &&
      deps.fence.isCurrent(token)
    );
  }

  /** Terminate the currently desired departure: keep the source and its work. */
  function terminateDesired(publishSource: boolean): void {
    const entry = desired;
    desired = null;
    selected = null;
    stage = "idle";
    if (entry !== null) {
      switch (entry.kind) {
        case "route":
          entry.resolve("failed");
          break;
        case "saveAs":
          entry.resolve("failed");
          break;
        case "recover":
          break;
      }
    }
    if (publishSource) {
      deps.projectAddress(deps.installedSource());
    }
  }

  /** Start the shared source barrier for the desired departure. */
  function startDeparture(): void {
    const entry = desired;
    if (entry === null || entry.kind === "recover") {
      return;
    }
    if (!deps.isEditing()) {
      // A copy never starts outside editing: Spara som stores first, and no
      // store runs while the gate does not admit writes.
      if (entry.kind === "saveAs") {
        terminateDesired(false);
        return;
      }
      // A clean loading or readonly source is left at once without settling,
      // but kept unconfirmed work in a source that cannot settle is never
      // silently abandoned.
      if (deps.hasUnconfirmed()) {
        terminateDesired(true);
        return;
      }
      selectDesired();
      dispatchSelected();
      return;
    }
    if (entry.kind === "route" && !deps.hasActiveStore() && deps.isVisibleDirty()) {
      // An ordinary address request from an otherwise idle source with
      // visible edits stays: the source keeps its address and its work.
      terminateDesired(true);
      return;
    }
    deps.captureKept();
    stage = "settling";
    const token = deps.fence.begin();
    void runBarrier(token);
  }

  function advance(): void {
    if (deps.isDisposed() || desired === null) {
      return;
    }
    if (stage === "settling") {
      // The shared barrier is already running: the replaced slot is all the
      // newer request needs. No second settle, no second dirty check.
      return;
    }
    if (stage === "running") {
      const entry = desired;
      if (entry.kind === "saveAs") {
        // A copy never starts behind a running replacement.
        terminateDesired(false);
        return;
      }
      // A newer target retires the running selection through the fence and
      // selects the newer target at once.
      selectDesired();
      dispatchSelected();
      return;
    }
    startDeparture();
  }

  /**
   * Settle the source under the existing lock with the existing flush. After
   * the settle, still inside the held lock, wait for an in-flight router
   * navigation (and its synchronous intent submit), so the winner selected
   * below is the latest request rather than the latest submit that beat the
   * navigation race. On success admit the winner synchronously (see
   * `selectDesired`). A failed or refused settle opens and retires nothing:
   * it terminates the currently desired departure. A stale completion after
   * an event moved the generation does nothing.
   */
  async function runBarrier(token: FenceToken): Promise<void> {
    const outcome = await deps.replaceCopy(async () => {
      const settled = await deps.settleEdit();
      if (!settled) {
        return "failed" as const;
      }
      await deps.waitForRouterIdle();
      if (deps.isDisposed() || !deps.fence.isCurrent(token)) {
        return "stale" as const;
      }
      deps.abandonAttempt();
      deps.captureKept();
      if (deps.isDisposed() || !deps.fence.isCurrent(token)) {
        return "stale" as const;
      }
      if (deps.hasUnconfirmed()) {
        return "unconfirmed" as const;
      }
      selectDesired();
      return "selected" as const;
    });
    if (outcome === "selected") {
      dispatchSelected();
      return;
    }
    if (outcome === "stale") {
      return;
    }
    terminateDesired(true);
  }

  function dispatchSelected(): void {
    const current = selected;
    if (current === null) {
      return;
    }
    if (current.entry.kind === "route") {
      void runRoute(current.entry, current.token);
    } else {
      void runCopy(current.entry, current.token);
    }
  }

  /** The explicit gate-owned opening transition: installation already ran in
   * the selected context; the gate adopts the lineage with a step-list load
   * and the lease claims it, exactly once per selection. */
  function adoptSelected(lineageId: string): void {
    deps.adoptSelectedOpening(lineageId);
    deps.claimSelectedLease(lineageId);
  }

  function finishSelected(entry: ExamWorkspaceReplacementSelected): void {
    if (desired !== null && desired.intent === entry.intent) {
      desired = null;
    }
    selected = null;
    stage = "idle";
  }

  async function runRoute(entry: ExamWorkspaceReplacementRouteEntry, token: FenceToken): Promise<void> {
    const intent = entry.intent;
    const outcome = await deps.openRouteTarget(intent.lineage, token);
    if (!isSelected(entry, token)) {
      return;
    }
    if (outcome === "installed") {
      adoptSelected(intent.lineage);
      finishSelected(entry);
      entry.resolve("installed");
      return;
    }
    // The selected target failed while current: recover the retained source
    // through the ordinary fresh-load path in a new current context. A newer
    // intent supersedes that recovery like any other replacement.
    selected = null;
    const retained = deps.installedSource();
    desired = { intent: { kind: "recover", source: retained }, kind: "recover" };
    deps.projectAddress(retained);
    deps.recoverRetainedSource();
    deps.notifyRouteFailed();
    entry.resolve("failed");
  }

  async function runCopy(entry: ExamWorkspaceReplacementSaveAsEntry, token: FenceToken): Promise<void> {
    const intent = entry.intent;
    if (!isSelected(entry, token)) {
      return;
    }
    const posting = deps.beginCopy(intent.source, intent.name);
    if (posting === null) {
      if (isSelected(entry, token)) {
        finishSelected(entry);
        entry.resolve("failed");
      }
      return;
    }
    const settled = await deps.fence.settle(token, posting);
    // A newer route retires the copy candidate: a late copy is neither
    // installed, projected nor deleted.
    if (!isSelected(entry, token) || settled.kind === "stale") {
      return;
    }
    if (settled.kind === "failed") {
      finishSelected(entry);
      const taken = isCopyNameTaken(settled.error);
      entry.resolve(taken ? "name_taken" : "failed");
      if (!taken) {
        deps.notifyCopyFailed();
      }
      return;
    }
    // Current-copy success adopts its response through the same opening
    // transition, once.
    deps.installReplacementDocument(token, settled.value);
    if (!isSelected(entry, token)) {
      return;
    }
    const lineageId = settled.value.summary.lineage_id;
    adoptSelected(lineageId);
    finishSelected(entry);
    deps.projectAddress(lineageId);
    entry.resolve("saved");
  }

  /**
   * Submit a route-open intent. Recorded synchronously before any await; a
   * duplicate echo for the currently desired target coalesces with it.
   */
  function submitRoute(lineageId: string): Promise<ExamWorkspaceRouteOpenOutcome> {
    if (deps.isDisposed()) {
      return Promise.resolve("superseded");
    }
    const current = desired;
    if (current !== null) {
      switch (current.kind) {
        case "route":
          if (current.intent.lineage === lineageId) {
            return current.promise;
          }
          break;
        case "saveAs":
        case "recover":
          break;
      }
    }
    replaceDesired();
    let resolve: (outcome: ExamWorkspaceRouteOpenOutcome) => void = () => undefined;
    const promise = new Promise<ExamWorkspaceRouteOpenOutcome>((run) => {
      resolve = run;
    });
    desired = { intent: { kind: "route", lineage: lineageId }, kind: "route", promise, resolve };
    advance();
    return promise;
  }

  /**
   * Submit a Spara som intent. Registered before its first await and sharing
   * the source barrier: a route that supersedes it during the wait still
   * settles the source, but the obsolete copy POST is never dispatched; a
   * failed shared flush runs neither copy nor open.
   */
  function submitSaveAs(name: string): Promise<ExamWorkspaceSaveAsOutcome> {
    const origin = deps.installedSource();
    if (deps.isDisposed() || origin === null) {
      return Promise.resolve("failed");
    }
    const current = desired;
    if (current !== null) {
      switch (current.kind) {
        case "saveAs":
          if (current.intent.source === origin && current.intent.name === name) {
            return current.promise;
          }
          break;
        case "route":
        case "recover":
          break;
      }
    }
    replaceDesired();
    let resolve: (outcome: ExamWorkspaceSaveAsOutcome) => void = () => undefined;
    const promise = new Promise<ExamWorkspaceSaveAsOutcome>((run) => {
      resolve = run;
    });
    desired = { intent: { kind: "saveAs", source: origin, name }, kind: "saveAs", promise, resolve };
    advance();
    return promise;
  }

  /** A lifecycle event retired the source generation: the pending barrier or
   * selection is stale, so terminate the desired departure. The event owns
   * the outcome; the coordinator keeps the source and projects its address. */
  function notifySourceRetired(): void {
    if (stage === "idle") {
      return;
    }
    terminateDesired(true);
  }

  /** The page is going away: terminate silently. Late results publish
   * nothing: no document, address, toast, status or cleanup. */
  function notifyPageHidden(): void {
    if (stage === "idle") {
      return;
    }
    terminateDesired(false);
  }

  function dispose(): void {
    terminateDesired(false);
  }

  return {
    currentAddress,
    dispose,
    notifyPageHidden,
    notifySourceRetired,
    submitRoute,
    submitSaveAs,
  };
}

export type ExamWorkspaceReplacementCoordinator = ReturnType<typeof createReplacementCoordinator>;
