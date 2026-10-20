/**
 * Exam workspace edit lease heartbeat: the renew and retry-claim cadence.
 *
 * Domain purpose:
 *   Every 5 s a held lease renews against the driver, and a read-only tab
 *   retries its refused claim at the same cadence, taking the lease as soon
 *   as it is free with no `Ta över`. Every answer settles through the gate's
 *   fence with a token begun before the call, and only a `current` answer
 *   touches lease state. A renew that reports another tab's takeover ask
 *   yields only after the fence admits that generation: the holder stores
 *   its pending edit, releases and turns read-only. In-flight renews settle
 *   in order, one sequence number per request, so an older result never
 *   overwrites a newer one. A lost lease keeps the heartbeat so the next
 *   tick retries the claim.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceEditLease`, which keeps the read-only state,
 *     the driver and the release paths, and passes them in as deps; this
 *     module owns only the cadence, the renew sequencing and the yield.
 *   - The claim side (open claim, `Ta över` poll) lives in
 *     `examWorkspaceEditLeaseAcquisition.ts` and shares the same fence.
 */

import type { Ref } from "vue";

import type { FenceToken, Settled, SyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceEditLeaseDriver } from "./examWorkspaceEditLeaseDrivers";

export type ExamWorkspaceEditLeaseHeartbeatDeps = {
  lineageId: () => string | null;
  isDisposed: () => boolean;
  holding: Ref<boolean>;
  /** The last successful claim or renew, as milliseconds from the lease clock. */
  lastSuccess: { value: number };
  /** The lease clock; specs control lease expiry through it. */
  clock: () => number;
  /** How often the holder renews; matches the server's 5 s heartbeat. */
  heartbeatMs: number;
  /** The lease TTL; a lease not renewed within it is dead. */
  ttlMs: number;
  /** The gate's fence: every renew and retry-claim answer settles through it. */
  fence: SyncFence;
  ensureDriver: () => ExamWorkspaceEditLeaseDriver | null;
  /** A stale answer frees only an abandoned grant, never the live lease. */
  isAbandonedGrant: (lineageId: string) => boolean;
  tryRelease: (lineageId: string, keepalive?: boolean) => Promise<void>;
  /** The single route from lease state to the gate. */
  setHolding: (held: boolean) => void;
  /** A yielded or refused tab turns read-only but keeps the heartbeat. */
  noteLostLease: () => void;
  /** Turn read-only and restart the heartbeat after yielding to a takeover. */
  noteYielded: () => void;
  /** Store the pending edit before yielding to a takeover. */
  onTakeoverRequested: () => Promise<void> | void;
  /** Settle one retry-claim answer through the fence, releasing a stale win. */
  settleClaimAnswer: (
    token: FenceToken,
    answer: Promise<"held" | "readonly" | "failed">,
    lineageId: string,
  ) => Promise<Settled<"held" | "readonly" | "failed">>;
  /** True while `Ta över` waits: the wait claims on its own faster poll. */
  isTakeoverWaiting: () => boolean;
  /** A successful retry claim for the current lineage grants editability. */
  noteAcquired: (lineageId: string) => Promise<void>;
};

export function createLeaseHeartbeat(deps: ExamWorkspaceEditLeaseHeartbeatDeps) {
  let heartbeat: ReturnType<typeof setInterval> | null = null;
  // In-flight renew ordering: every request takes a sequence number, and a
  // result older than one already applied is ignored.
  let renewSeq = 0;
  let appliedRenewSeq = 0;

  function stop(): void {
    if (heartbeat !== null) {
      clearInterval(heartbeat);
      heartbeat = null;
    }
  }

  function start(): void {
    // The guest controller renews on its own heartbeat too; this second
    // heartbeat is what surfaces a lost guest lease in the read-only state,
    // which the controller's silent stop would otherwise hide.
    if (heartbeat !== null || deps.isDisposed()) {
      return;
    }
    heartbeat = setInterval(() => {
      void tick();
    }, deps.heartbeatMs);
  }

  /** Store the pending edit, release and turn read-only for the waiting tab. */
  async function yieldLease(lineageId: string, token: FenceToken): Promise<void> {
    // The renew answer already passed the fence; the awaited continuation
    // below rechecks the same token, so an answer retired mid-yield flushes
    // nothing, releases nothing and changes no holding.
    if (!deps.fence.isCurrent(token)) {
      return;
    }
    try {
      await deps.onTakeoverRequested();
    } finally {
      await releaseIfCurrent(lineageId, token);
    }
  }

  /** Release and yield only while the renew token is still current. */
  async function releaseIfCurrent(lineageId: string, token: FenceToken): Promise<void> {
    if (!deps.fence.isCurrent(token)) {
      return;
    }
    await deps.tryRelease(lineageId);
    if (deps.fence.isCurrent(token)) {
      deps.noteYielded();
    }
  }

  async function tick(): Promise<void> {
    if (deps.isDisposed()) {
      return;
    }
    const lineageId = deps.lineageId();
    const active = deps.ensureDriver();
    if (lineageId === null || active === null) {
      return;
    }
    // A read-only tab retries its refused claim at the heartbeat cadence and
    // takes the lease as soon as it is free, with no `Ta över`. A waiting
    // takeover claims on its own faster poll instead. A `failed` retry claim
    // stays read-only; only the claim on open stays editable on such a
    // failure.
    if (!deps.holding.value) {
      if (deps.isTakeoverWaiting()) {
        return;
      }
      const token = deps.fence.begin();
      const settled = await deps.settleClaimAnswer(token, active.claim(lineageId), lineageId);
      if (settled.kind === "stale" || settled.kind === "failed") {
        return;
      }
      if (deps.isDisposed() || deps.lineageId() !== lineageId) {
        if (settled.value === "held" && deps.isAbandonedGrant(lineageId)) {
          await deps.tryRelease(lineageId);
        }
        return;
      }
      if (deps.holding.value) {
        // A duplicate success for the still-current owner: another in-flight
        // claim already established holding. No-op, never release.
        return;
      }
      if (settled.value === "held") {
        await deps.noteAcquired(lineageId);
      }
      return;
    }
    // The local deadline is enforced before awaiting: a holder whose last
    // success is past the TTL turns read-only even while a renew is still
    // pending. The next ticks then retry the claim at the heartbeat cadence.
    if (deps.clock() - deps.lastSuccess.value >= deps.ttlMs) {
      deps.noteLostLease();
      return;
    }
    const seq = renewSeq + 1;
    renewSeq = seq;
    const sentAt = deps.clock();
    const token = deps.fence.begin();
    const settled = await deps.fence.settle(token, active.renew(lineageId));
    if (settled.kind === "stale") {
      // A renew answer that settles stale updates neither `holding` nor the
      // last-success time. The M2 window below runs only on current answers.
      return;
    }
    // In-flight renews settle in order: a result older than one already
    // applied is ignored, so an earlier success cannot overwrite a later
    // loss.
    if (seq <= appliedRenewSeq) {
      return;
    }
    appliedRenewSeq = seq;
    if (deps.isDisposed() || deps.lineageId() !== lineageId) {
      return;
    }
    const renewed = settled.kind === "failed" ? "failed" : settled.value;
    if (renewed === "takeover") {
      // The driver reported another tab's `Ta över` ask without acting on
      // it; yield only now that the fence admitted this generation. A
      // genuine current-generation takeover still flushes, releases, turns
      // read-only and restarts the heartbeat through `yieldLease`.
      await yieldLease(lineageId, token);
    } else if (renewed === "held") {
      // A late success never revives a lease that was lost or expired while
      // it was in flight, and it extends the deadline only from the time its
      // request was sent, never from the receipt time.
      if (!deps.holding.value || deps.clock() - sentAt >= deps.ttlMs) {
        deps.noteLostLease();
        return;
      }
      deps.lastSuccess.value = sentAt;
      deps.setHolding(true);
    } else if (renewed === "lost") {
      deps.setHolding(false);
    } else if (deps.clock() - deps.lastSuccess.value >= deps.ttlMs) {
      // Renewals kept failing past the lease TTL, so the server lease is
      // dead: turn read-only. The next ticks retry the claim and take the
      // lease back as soon as it is free.
      deps.noteLostLease();
    }
    // A lost lease keeps the heartbeat: the next tick retries the claim and
    // takes the lease back as soon as it is free.
  }

  return { start, stop };
}
