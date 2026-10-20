/**
 * Exam workspace edit lease acquisition (TASK-SKRIPT-40-04-14, F3 step 1-4).
 *
 * Domain purpose:
 *   The claim side of the edit lease: the claim on open, the retry-claim
 *   success path shared with the heartbeat and the takeover poll, and
 *   `Ta över` itself. Every answer settles through the gate's fence with a
 *   token begun before the call, and lease state changes only on `current`.
 *   Only the claim on open stays editable on a failure that is not a live
 *   foreign lease; every retry claim keeps read-only and retries. A claim
 *   that won on the server but settles `stale` is still released server-side
 *   (a transport action, never client state). `renewSeq` orders answers
 *   inside one generation and is not a lifetime check.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceEditLease`, which keeps the read-only state,
 *     the heartbeat, the driver and the release paths, and passes them in as
 *     deps; this module owns only the takeover poll, the waiting flag and the
 *     claim entries. The heartbeat's retry claim settles through
 *     `settleClaimAnswer` here so both claim paths share the release rule.
 *   - Runs one attempt per poll through the drivers in
 *     `examWorkspaceEditLeaseDrivers.ts`; the composable retries a refused
 *     claim at the heartbeat cadence outside the wait.
 */

import { computed } from "vue";
import { ref } from "vue";
import type { Ref } from "vue";

import type { FenceToken, Settled, SyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceEditLeaseDriver } from "./examWorkspaceEditLeaseDrivers";
import { createTakeoverPoll } from "./examWorkspaceEditLeaseTakeover";

export type ExamWorkspaceEditLeaseAcquisitionDeps = {
  lineageId: () => string | null;
  isDisposed: () => boolean;
  holding: Ref<boolean>;
  /** The last successful claim or renew, as milliseconds from the lease clock. */
  lastSuccess: { value: number };
  /** The lease clock; specs control lease expiry through it. */
  clock: () => number;
  /** The gate's fence: every claim and takeover answer settles through it. */
  fence: SyncFence;
  ensureDriver: () => ExamWorkspaceEditLeaseDriver | null;
  /** A stale answer frees only an abandoned lineage, never the live lease. */
  isAbandonedLineage: (lineageId: string) => boolean;
  tryRelease: (lineageId: string, keepalive?: boolean) => Promise<void>;
  /** The single route from lease state to the gate. */
  setHolding: (held: boolean) => void;
  /** The open claim ended without holding: the gate reports `leaseRefused`. */
  onClaimRefused: () => void;
  startHeartbeat: () => void;
  /** How long a waiting `Ta över` sleeps between poll claims. */
  takeoverPollMs: number;
};

export function createLeaseAcquisition(deps: ExamWorkspaceEditLeaseAcquisitionDeps) {
  const waiting = ref(false);
  const takeoverPoll = createTakeoverPoll(deps.takeoverPollMs);
  /**
   * The lineage whose open claim is still in flight, if any. Heartbeat retry
   * claims never set it: only the open claim decides a deferred gate load.
   * Compared by lineage, so a stale open claim settling after a lineage
   * switch never clears the new exam's wait.
   */
  let pendingClaimLineage: string | null = null;

  function stopWaiting(): void {
    waiting.value = false;
    // Wake a sleeping takeover poll so `requestTakeover` settles on
    // cancellation instead of staying pending forever.
    takeoverPoll.cancel();
  }

  /**
   * Release a stale win only when its lineage is abandoned: the server lease
   * is keyed by lineage and this tab's id, so a stale grant for the lineage
   * this tab currently claims or holds is the same server lease as the
   * current visit and must never be released. Only a grant for a lineage the
   * composable no longer claims or holds (or a disposed composable) is
   * genuinely abandoned. First-claim-wins stays: the live lease is untouched.
   */
  function releaseStaleGrant(staleLineage: string): void {
    if (deps.isAbandonedLineage(staleLineage)) {
      void deps.tryRelease(staleLineage);
    }
  }

  /**
   * Settle one claim answer through the fence. A win that settles stale was
   * granted on the server after its generation retired, so it is released
   * server-side when its lineage is abandoned, and never touches `holding`.
   */
  function settleClaimAnswer(
    token: FenceToken,
    answer: Promise<"held" | "readonly" | "failed">,
    lineageId: string,
  ): Promise<Settled<"held" | "readonly" | "failed">> {
    void answer.then(
      (outcome) => {
        if (outcome === "held" && !deps.fence.isCurrent(token)) {
          releaseStaleGrant(lineageId);
        }
      },
      () => undefined,
    );
    return deps.fence.settle(token, answer);
  }

  async function claimCurrent(lineageId: string): Promise<void> {
    // Synchronous with the `openLineage` call, so the gate's synchronous
    // claim-in-flight read sees the open claim from its first microtask.
    pendingClaimLineage = lineageId;
    try {
      const active = deps.ensureDriver();
      if (active === null) {
        deps.setHolding(true);
        return;
      }
      const token = deps.fence.begin();
      const settled = await settleClaimAnswer(token, active.claim(lineageId), lineageId);
      if (settled.kind === "stale") {
        return;
      }
      // Only the claim on open stays editable on a failure that is not a
      // live foreign lease; every retry claim keeps read-only and retries.
      const outcome: "held" | "readonly" =
        settled.kind === "failed" || settled.value === "failed" ? "held" : settled.value;
      if (deps.isDisposed() || deps.lineageId() !== lineageId) {
        if (outcome === "held" && deps.isAbandonedLineage(lineageId)) {
          await deps.tryRelease(lineageId);
        } else if (outcome === "readonly" && deps.lineageId() === null) {
          // The drawer closed mid-open with no newer lineage: the gate still
          // waits on this claim, so report the refusal instead of leaving it
          // deferred. A switch to another lineage stays silent; its own claim
          // decides the gate.
          deps.onClaimRefused();
        }
        return;
      }
      if (outcome === "held") {
        deps.lastSuccess.value = deps.clock();
        deps.setHolding(true);
      } else {
        // Holding is already false after the `openLineage` reset, so this
        // reports nothing through `setHolding`. Tell the gate through the
        // refusal route so a load deferred on this claim resolves read-only.
        deps.onClaimRefused();
      }
      // The heartbeat both renews a held lease and retries a refused claim, so
      // a reloaded tab takes the lease as soon as it is free, with no `Ta över`.
      deps.startHeartbeat();
    } finally {
      if (pendingClaimLineage === lineageId) {
        pendingClaimLineage = null;
      }
    }
  }

  async function noteAcquired(lineageId: string): Promise<void> {
    // A late success for an abandoned lineage is released instead of
    // granting editability; the current live lease is never revoked.
    if (deps.isDisposed() || deps.lineageId() !== lineageId) {
      if (deps.isAbandonedLineage(lineageId)) {
        await deps.tryRelease(lineageId);
      }
      return;
    }
    if (deps.holding.value) {
      // A duplicate success for the still-current owner: another in-flight
      // claim already established holding. No-op, never release.
      return;
    }
    deps.lastSuccess.value = deps.clock();
    deps.setHolding(true);
    stopWaiting();
    deps.startHeartbeat();
  }

  /** Settle one takeover-request answer; a stale grant for an abandoned lineage is released. */
  function settlePollRequest(
    active: ExamWorkspaceEditLeaseDriver,
    token: FenceToken,
    lineageId: string,
  ): Promise<"claimed" | "requested" | "own"> {
    const answer = active.requestTakeover(lineageId);
    void answer.then(
      (outcome) => {
        if ((outcome === "claimed" || outcome === "own") && !deps.fence.isCurrent(token)) {
          releaseStaleGrant(lineageId);
        }
      },
      () => undefined,
    );
    return deps.fence.settle(token, answer).then((settled) => {
      if (settled.kind === "stale" || settled.kind === "failed") {
        return "requested";
      }
      return settled.value;
    });
  }

  /** Settle one poll-claim answer; a stale win for an abandoned lineage is released. */
  function settlePollClaim(
    active: ExamWorkspaceEditLeaseDriver,
    token: FenceToken,
    lineageId: string,
  ): Promise<"held" | "readonly" | "failed"> {
    const answer = active.claim(lineageId);
    void answer.then(
      (outcome) => {
        if (outcome === "held" && !deps.fence.isCurrent(token)) {
          releaseStaleGrant(lineageId);
        }
      },
      () => undefined,
    );
    return deps.fence.settle(token, answer).then((settled) => {
      if (settled.kind === "stale" || settled.kind === "failed") {
        // A `failed` poll claim stays waiting like a refused one; only the
        // claim on open stays editable on such a failure.
        return "readonly";
      }
      return settled.value;
    });
  }

  /**
   * `Ta över`: record the request, claim at once when the lease is already
   * free, else poll the claim until the holder releases or its lease dies,
   * then read the newest state. While waiting the tab stays read-only.
   */
  async function requestTakeover(): Promise<void> {
    const lineageId = deps.lineageId();
    const active = deps.ensureDriver();
    if (lineageId === null || active === null || deps.holding.value || waiting.value || deps.isDisposed()) {
      return;
    }
    const fenced: ExamWorkspaceEditLeaseDriver = {
      ...active,
      claim: (claimLineage: string) => settlePollClaim(active, deps.fence.begin(), claimLineage),
      requestTakeover: (takeoverLineage: string) =>
        settlePollRequest(active, deps.fence.begin(), takeoverLineage),
    };
    const isCurrent = (): boolean => !deps.isDisposed() && deps.lineageId() === lineageId;
    waiting.value = true;
    try {
      await takeoverPoll.run(fenced, lineageId, {
        isCurrent,
        noteAcquired,
        noteOwn: () => {
          deps.lastSuccess.value = deps.clock();
          deps.setHolding(true);
          stopWaiting();
          deps.startHeartbeat();
        },
        release: (staleLineage: string) => {
          if (deps.isAbandonedLineage(staleLineage)) {
            return deps.tryRelease(staleLineage);
          }
          return Promise.resolve();
        },
        shouldWait: () => waiting.value && !deps.holding.value,
      });
    } finally {
      if (!deps.holding.value) {
        stopWaiting();
      }
    }
  }

  return {
    claimCurrent,
    isClaimPending: () => pendingClaimLineage !== null,
    noteAcquired,
    requestTakeover,
    settleClaimAnswer,
    stopWaiting,
    /** True while `Ta över` waits for the holder to release. */
    waiting: computed(() => waiting.value),
  };
}
