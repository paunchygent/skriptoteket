/**
 * Exam workspace edit lease: one editing tab per exam.
 *
 * Domain purpose:
 *   One tab at a time edits an exam (TASK-SKRIPT-40-04-14 behaviour item 7,
 *   decision D4). Each page load has a random tab id; opening an exam claims
 *   the edit lease, and a tab that does not hold it stays read-only. The
 *   holder renews the lease every 5 s, and a lease not renewed for 15 s is
 *   dead, so a crashed tab stops blocking after 15 s. Every write carries the
 *   tab id, and a write refused with `EDIT_LEASE_HELD` turns the holder
 *   read-only through `noteLostLease` while its pending edit stays visible;
 *   a yielded or refused tab keeps retrying its claim at the heartbeat
 *   cadence and takes the lease back as soon as it is free, with no
 *   `Ta över`. The holder sees a takeover request at its next renew: it stores its
 *   pending edit, releases the lease and turns read-only. `Ta över` requests
 *   the lease and claims it once the holder has released or its lease has
 *   expired, then reads the newest state. A closed tab releases its lease on
 *   `pagehide` with `keepalive`, so the release reaches the server after the
 *   page is gone. A claim refused with `EDIT_LEASE_HELD` opens read-only and
 *   retries at the heartbeat cadence, taking the lease as soon as it is free
 *   (expired or released) with no `Ta över`. Only the claim on open stays
 *   editable on any other claim failure, since the write guard is
 *   authoritative and refuses a tab without the lease; every retry claim
 *   (the read-only heartbeat, the `Ta över` poll and the claim inside
 *   `requestTakeover`) treats such a failure as stay read-only and retries
 *   at the next tick or poll, so one failed request never turns a read-only
 *   tab editable while another tab holds the lease. After yielding to a
 *   takeover the tab restarts its heartbeat, so its first retry claim
 *   happens one full heartbeat after the release instead of racing the
 *   waiting tab's poll; a refused write keeps its heartbeat phase. A holder
 *   whose renewals keep failing stays editable only while its last
 *   successful claim or renew is within the 15 s lease TTL; once the TTL
 *   has passed it turns read-only, keeps retrying the claim at the
 *   heartbeat cadence and reads the newest state when it takes the lease
 *   back. The local deadline is enforced on every heartbeat tick before
 *   awaiting, so the holder turns read-only even while a renew is still
 *   pending. In-flight renews settle in order, one sequence number per
 *   request: an older result never overwrites a newer one, a late success
 *   never revives a lost or expired lease, and a success extends the
 *   deadline only from the time its request was sent. Takeover and claim
 *   work is tied to an identity (the lineage plus the gate's generation):
 *   the generation is retired before a new lineage claims, every answer
 *   settles through the fence, and only a `current` answer touches lease
 *   state. A claim that won on the server but settles `stale` is released
 *   server-side instead of granting editability, and a stale renew updates
 *   neither holding nor the last-success time. Cancelling wakes a sleeping
 *   poll.
 *
 * Relationships:
 *   - The server half runs on the edit-lease transport of
 *     `api/examWorkspace.ts` through the drivers in
 *     `examWorkspaceEditLeaseDrivers.ts`. The guest half drives K7's
 *     `createGuestEditLeaseController` against the IndexedDB-bound lease slot
 *     (`createIndexedDbGuestEditLeaseStorage`), whose own heartbeat, channel
 *     signal and `pagehide` release answer takeovers. The composable owns the
 *     read-only state, its own heartbeat (which both renews the held lease
 *     and retries a refused claim), the takeover wait and `pagehide`
 *     release in both modes; the guest controller's heartbeat stays as a
 *     redundant poller.
 *   - Owned by `useExamWorkspaceEditing`, which feeds the tab id into the
 *     history and structure writes, stores the pending edit on a takeover
 *     request and reloads the newest state on acquiring the lease; the view
 *     shows `Öppet i en annan flik` with `Ta över` while read-only.
 */

import { computed, onScopeDispose, ref } from "vue";

import {
  createGuestDriver,
  createServerDriver,
  isEditLeaseHeldError,
  type ExamWorkspaceEditLeaseDriver,
  type ExamWorkspaceEditLeaseServer,
} from "./examWorkspaceEditLeaseDrivers";
export { isEditLeaseHeldError };
export type { ExamWorkspaceEditLeaseServer };
import {
  claimExamWorkspaceEditLease,
  releaseExamWorkspaceEditLease,
  renewExamWorkspaceEditLease,
  requestExamWorkspaceEditLeaseTakeover,
} from "../../../api/examWorkspace";
import {
  createLeaseAcquisition,
} from "./examWorkspaceEditLeaseAcquisition";
import type { SyncFence } from "./examWorkspaceSyncFence";
import {
  createGuestEditLeaseChannel,
  type GuestEditLeaseChannel,
  type GuestEditLeaseStoragePort,
} from "./examWorkspaceGuestEditLease";
import { createIndexedDbGuestEditLeaseStorage } from "./examWorkspaceGuestDraftStorage";

/** How often the holder renews the server lease; matches the server's 5 s heartbeat. */
export const EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS = 5_000;
/** A lease not renewed within this long is dead; matches the server's 15 s expiry. */
export const EXAM_WORKSPACE_EDIT_LEASE_TTL_MS = 15_000;
/** How often a waiting `Ta över` retries the claim until the lease is free. */
export const EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS = 1_000;

/** A random tab id per page load; a reload is a new tab. */
export function createExamWorkspaceEditLeaseTabId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const defaultServer: ExamWorkspaceEditLeaseServer = {
  claim: (lineageId, tabId) => claimExamWorkspaceEditLease(lineageId, tabId),
  release: (lineageId, tabId, options) =>
    releaseExamWorkspaceEditLease(lineageId, tabId, options),
  renew: (lineageId, tabId) => renewExamWorkspaceEditLease(lineageId, tabId),
  requestTakeover: (lineageId, tabId) => requestExamWorkspaceEditLeaseTakeover(lineageId, tabId),
};

export type ExamWorkspaceEditLeaseDeps = {
  lineageId: () => string | null;
  isGuest: () => boolean;
  /** The server lease calls; specs inject a double, production uses the transport. */
  server?: ExamWorkspaceEditLeaseServer;
  /** The IndexedDB-bound lease slot for guests; specs inject the in-memory port. */
  guestStorage?: GuestEditLeaseStoragePort;
  openGuestChannel?: () => GuestEditLeaseChannel;
  /** The guest clock; specs control lease expiry through it. */
  now?: () => number;
  /** A fixed tab id for specs; production always rolls a random one. */
  tabId?: string;
  /** The gate's fence: every claim, renew, takeover and release answer settles through it. */
  fence: SyncFence;
  /** Store the pending edit before yielding to a takeover. */
  onTakeoverRequested: () => Promise<void> | void;
  /** Held became true: the gate reports `leaseAcquired`. Exactly one call per transition. */
  onLeaseAcquired: () => void;
  /** Held became false: the gate reports `leaseLost`. Exactly one call per transition. */
  onLeaseLost: () => void;
};

export function useExamWorkspaceEditLease(deps: ExamWorkspaceEditLeaseDeps) {
  const tabId = deps.tabId ?? createExamWorkspaceEditLeaseTabId();
  const guest = deps.isGuest();
  const holding = ref(false);
  const readOnly = computed(() => !holding.value);
  let disposed = false;
  let driver: ExamWorkspaceEditLeaseDriver | null = null;
  let heartbeat: ReturnType<typeof setInterval> | null = null;
  const clock = deps.now ?? (() => Date.now());
  const lastSuccess = { value: clock() };
  // The lineage the last open claim started for; the editing session calls
  // `openLineage` after `gate.openExam`, so the previous lease releases here.
  let claimedLineage: string | null = null;
  // In-flight renew ordering: every request takes a sequence number, and a
  // result older than one already applied is ignored.
  let renewSeq = 0;
  let appliedRenewSeq = 0;

  function stopHeartbeat(): void {
    if (heartbeat !== null) {
      clearInterval(heartbeat);
      heartbeat = null;
    }
  }

  /**
   * The single route from lease state to the gate: every `holding` change
   * synchronously reports held-became-true as `leaseAcquired` and
   * held-became-false as `leaseLost`. Transitions that change nothing
   * report nothing, so the gate sees exactly one callback per transition.
   */
  function setHolding(next: boolean): void {
    if (holding.value === next) {
      return;
    }
    holding.value = next;
    if (disposed) {
      return;
    }
    if (next) {
      deps.onLeaseAcquired();
    } else {
      deps.onLeaseLost();
    }
  }

  function noteLostLease(): void {
    // A yielded or refused tab stays read-only but keeps the heartbeat: the
    // next ticks retry the claim at the heartbeat cadence and take the lease
    // back as soon as it is free, exactly like a tab that opened read-only.
    // Only dispose, the lineage switch and `pagehide` stop the heartbeat.
    setHolding(false);
  }

  /** A stale answer frees only an abandoned lineage, never the live lease. */
  function isAbandonedLineage(lineageId: string): boolean {
    if (disposed) {
      return true;
    }
    return deps.lineageId() !== lineageId;
  }

  async function tryRelease(lineageId: string, keepalive = false): Promise<void> {
    if (driver === null) {
      return;
    }
    const token = deps.fence.begin();
    try {
      // Only the `pagehide` release carries options, so the recorded calls
      // of every other release keep their two-argument shape. The answer
      // settles through the fence; a retired answer changes no lease state.
      if (keepalive) {
        await deps.fence.settle(token, driver.release(lineageId, { keepalive: true }));
      } else {
        await deps.fence.settle(token, driver.release(lineageId));
      }
    } catch {
      // Best effort: closing and yielding never fail the session.
    }
  }

  /** Turn read-only and restart the heartbeat after yielding to a takeover. */
  function noteYielded(): void {
    setHolding(false);
    // Restart the heartbeat so the first retry claim happens one full
    // heartbeat after the release, not on the old phase: otherwise this
    // tab could reclaim the freed lease before the waiting tab's `Ta över`
    // poll. A refused write keeps its phase through `noteLostLease`.
    stopHeartbeat();
    startHeartbeat();
  }

  /** Store the pending edit, release and turn read-only for the waiting tab. */
  async function yieldLease(lineageId: string): Promise<void> {
    try {
      await deps.onTakeoverRequested();
    } finally {
      await tryRelease(lineageId);
      noteYielded();
    }
  }

  function ensureDriver(): ExamWorkspaceEditLeaseDriver | null {
    if (driver !== null) {
      return driver;
    }
    try {
      driver = guest
        ? createGuestDriver(
            tabId,
            deps.guestStorage ?? createIndexedDbGuestEditLeaseStorage(),
            deps.openGuestChannel ?? createGuestEditLeaseChannel,
            deps.now,
            () => deps.onTakeoverRequested(),
            noteLostLease,
            noteYielded,
          )
        : createServerDriver(deps.server ?? defaultServer, tabId, yieldLease);
    } catch {
      driver = null;
    }
    return driver;
  }

  function startHeartbeat(): void {
    // The guest controller renews on its own heartbeat too; this second
    // heartbeat is what surfaces a lost guest lease in the read-only state,
    // which the controller's silent stop would otherwise hide.
    if (heartbeat !== null || disposed) {
      return;
    }
    heartbeat = setInterval(() => {
      void heartbeatTick();
    }, EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
  }

  async function heartbeatTick(): Promise<void> {
    if (disposed) {
      return;
    }
    const lineageId = deps.lineageId();
    const active = ensureDriver();
    if (lineageId === null || active === null) {
      return;
    }
    // A read-only tab retries its refused claim at the heartbeat cadence and
    // takes the lease as soon as it is free, with no `Ta över`. A waiting
    // takeover claims on its own faster poll instead. A `failed` retry claim
    // stays read-only; only the claim on open stays editable on such a
    // failure.
    if (!holding.value) {
      if (acquisition.waiting.value) {
        return;
      }
      const token = deps.fence.begin();
      const settled = await acquisition.settleClaimAnswer(token, active.claim(lineageId), lineageId);
      if (settled.kind === "stale" || settled.kind === "failed") {
        return;
      }
      if (disposed || deps.lineageId() !== lineageId) {
        if (settled.value === "held" && isAbandonedLineage(lineageId)) {
          await tryRelease(lineageId);
        }
        return;
      }
      if (holding.value) {
        // A duplicate success for the still-current owner: another in-flight
        // claim already established holding. No-op, never release.
        return;
      }
      if (settled.value === "held") {
        await acquisition.noteAcquired(lineageId);
      }
      return;
    }
    // The local deadline is enforced before awaiting: a holder whose last
    // success is past the TTL turns read-only even while a renew is still
    // pending. The next ticks then retry the claim at the heartbeat cadence.
    if (clock() - lastSuccess.value >= EXAM_WORKSPACE_EDIT_LEASE_TTL_MS) {
      noteLostLease();
      return;
    }
    const seq = renewSeq + 1;
    renewSeq = seq;
    const sentAt = clock();
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
    if (disposed || deps.lineageId() !== lineageId) {
      return;
    }
    const renewed = settled.kind === "failed" ? "failed" : settled.value;
    if (renewed === "held") {
      // A late success never revives a lease that was lost or expired while
      // it was in flight, and it extends the deadline only from the time its
      // request was sent, never from the receipt time.
      if (!holding.value || clock() - sentAt >= EXAM_WORKSPACE_EDIT_LEASE_TTL_MS) {
        noteLostLease();
        return;
      }
      lastSuccess.value = sentAt;
      setHolding(true);
    } else if (renewed === "lost") {
      setHolding(false);
    } else if (clock() - lastSuccess.value >= EXAM_WORKSPACE_EDIT_LEASE_TTL_MS) {
      // Renewals kept failing past the lease TTL, so the server lease is
      // dead: turn read-only. The next ticks retry the claim and take the
      // lease back as soon as it is free.
      noteLostLease();
    }
    // A lost lease keeps the heartbeat: the next tick retries the claim and
    // takes the lease back as soon as it is free.
  }


  const acquisition = createLeaseAcquisition({
    lineageId: deps.lineageId,
    isDisposed: () => disposed,
    holding,
    lastSuccess,
    clock,
    fence: deps.fence,
    ensureDriver,
    isAbandonedLineage,
    tryRelease,
    setHolding,
    startHeartbeat,
    takeoverPollMs: EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS,
  });

  /**
   * The editing session calls this after `gate.openExam`, which retires the
   * generation, so the open claim below begins a current token. The previous
   * lineage releases when this tab holds it; a null lineage only releases
   * and never claims.
   */
  function openLineage(next: string | null): void {
    acquisition.stopWaiting();
    const previous = claimedLineage;
    claimedLineage = next;
    if (previous !== null && previous !== next && holding.value) {
      void tryRelease(previous);
    }
    setHolding(false);
    stopHeartbeat();
    if (next !== null && !disposed) {
      void acquisition.claimCurrent(next);
    }
  }

  function handlePagehide(): void {
    const lineageId = deps.lineageId();
    acquisition.stopWaiting();
    if (lineageId !== null && holding.value) {
      // The page is going away: `keepalive` lets the browser finish the
      // release POST after the unload, or the old lease blocks the reloaded
      // tab until the 15 s TTL dies.
      void tryRelease(lineageId, true);
    }
  }

  const hasWindow = typeof window !== "undefined";
  if (hasWindow) {
    window.addEventListener("pagehide", handlePagehide);
  }

  onScopeDispose(() => {
    disposed = true;
    acquisition.stopWaiting();
    stopHeartbeat();
    const lineageId = deps.lineageId();
    if (driver !== null) {
      if (lineageId !== null && holding.value) {
        void tryRelease(lineageId);
      }
      driver.dispose();
      driver = null;
    }
    if (hasWindow) {
      window.removeEventListener("pagehide", handlePagehide);
    }
  });

  return {
    noteLostLease,
    openLineage,
    readOnly,
    requestTakeover: acquisition.requestTakeover,
    /** The tab id this page load writes with. */
    tabId,
    /** True while `Ta över` waits for the holder to release. */
    waiting: acquisition.waiting,
  };
}
