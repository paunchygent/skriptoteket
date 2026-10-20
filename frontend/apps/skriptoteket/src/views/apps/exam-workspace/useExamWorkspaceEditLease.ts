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
 *   page is gone. A `pagehide` clears the hold silently and retires the
 *   generation in every live gate phase through the page-hidden port, so a
 *   pending claim and load settle stale while the heartbeat keeps running
 *   and reclaims on return. A claim refused with `EDIT_LEASE_HELD` opens read-only and
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
 *   state. An open claim that ends without holding reports through the refusal
 *   route while holding stays false, so a gate load deferred on it resolves.
 *   A claim that won on the server but settles `stale` is released
 *   server-side instead of granting editability, and a stale renew updates
 *   neither holding nor the last-success time. A renew that sees another
 *   tab's takeover ask reports it without acting; the yield runs only after
 *   the fence admits the answer as current. Cancelling wakes a sleeping
 *   poll.
 *
 * Relationships:
 *   - The server half runs on the edit-lease transport of
 *     `api/examWorkspace.ts` through the drivers in
 *     `examWorkspaceEditLeaseDrivers.ts`. The guest half drives K7's
 *     `createGuestEditLeaseController` against the IndexedDB-bound lease slot
 *     (`createIndexedDbGuestEditLeaseStorage`), whose own heartbeat, channel
 *     signal and `pagehide` release answer takeovers. The composable owns the
 *     read-only state, the driver and the release paths; the heartbeat in
 *     `examWorkspaceEditLeaseHeartbeat.ts` renews the held lease and retries
 *     a refused claim, and the acquisition in
 *     `examWorkspaceEditLeaseAcquisition.ts` owns the open claim and the
 *     takeover wait. The guest controller's heartbeat stays as a redundant
 *     poller.
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
import { createLeaseHeartbeat } from "./examWorkspaceEditLeaseHeartbeat";
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
  /** The page hid: the gate retires the generation. Exactly one call per pagehide. */
  onPageHidden: () => void;
  /** The open claim ended without holding: the gate reports `leaseRefused`. */
  onLeaseRefused: () => void;
};

export function useExamWorkspaceEditLease(deps: ExamWorkspaceEditLeaseDeps) {
  const tabId = deps.tabId ?? createExamWorkspaceEditLeaseTabId();
  const guest = deps.isGuest();
  const holding = ref(false);
  const readOnly = computed(() => !holding.value);
  let disposed = false;
  let driver: ExamWorkspaceEditLeaseDriver | null = null;
  const clock = deps.now ?? (() => Date.now());
  const lastSuccess = { value: clock() };
  // The lineage the last open claim started for; the editing session calls
  // `openLineage` after `gate.openExam`, so the previous lease releases here.
  let claimedLineage: string | null = null;

  /**
   * The two routes from lease state to the gate: every `holding` change
   * synchronously reports held-became-true as `leaseAcquired` and
   * held-became-false as `leaseLost`, and an open claim that ends without
   * holding reports `leaseRefused` while holding stays false. Transitions
   * that change nothing report nothing, so the gate sees exactly one callback
   * per outcome.
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

  /** A stale answer frees only an abandoned grant, never the live lease. */
  function isAbandonedGrant(lineageId: string): boolean {
    if (disposed) {
      return true;
    }
    const current = deps.lineageId();
    if (current === null) {
      return true;
    }
    // A grant came from the driver that claimed it; with no driver there is
    // nothing to release.
    if (driver === null) {
      return false;
    }
    // Judge by the selected driver's ownership identity, not by lineage:
    // the server lease is keyed by lineage, but the guest lease is this
    // tab's single global slot. A stale guest win for another lineage still
    // owns the slot visited now, so it is never abandoned.
    return driver.leaseIdentity(current) !== driver.leaseIdentity(lineageId);
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
    heartbeat.stop();
    heartbeat.start();
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
            noteYielded,
            deps.fence,
          )
        : createServerDriver(deps.server ?? defaultServer, tabId);
    } catch {
      driver = null;
    }
    return driver;
  }

  const acquisition = createLeaseAcquisition({
    lineageId: deps.lineageId,
    isDisposed: () => disposed,
    holding,
    lastSuccess,
    clock,
    fence: deps.fence,
    ensureDriver,
    isAbandonedGrant,
    tryRelease,
    setHolding,
    onClaimRefused: () => {
      if (!disposed) {
        deps.onLeaseRefused();
      }
    },
    // Runs only after both modules exist below: claim and takeover paths
    // call it at runtime, never during construction.
    startHeartbeat: () => heartbeat.start(),
    takeoverPollMs: EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS,
  });

  const heartbeat = createLeaseHeartbeat({
    lineageId: deps.lineageId,
    isDisposed: () => disposed,
    holding,
    lastSuccess,
    clock,
    heartbeatMs: EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS,
    ttlMs: EXAM_WORKSPACE_EDIT_LEASE_TTL_MS,
    fence: deps.fence,
    ensureDriver,
    isAbandonedGrant,
    tryRelease,
    setHolding,
    noteLostLease,
    noteYielded,
    onTakeoverRequested: () => deps.onTakeoverRequested(),
    settleClaimAnswer: acquisition.settleClaimAnswer,
    isTakeoverWaiting: () => acquisition.waiting.value,
    noteAcquired: acquisition.noteAcquired,
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
    // The gate already moved through `openExam`, so this reset clears the
    // previous exam's hold without reporting a loss: reporting one would
    // retire the new exam's fresh load. Every other `holding` change still
    // reports through `setHolding`.
    holding.value = false;
    heartbeat.stop();
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
    // Clear the hold without reporting a lease loss, like the lineage switch
    // in `openLineage`: the page-hidden callback below is the single gate
    // report for this event, so the gate retires the generation exactly once
    // instead of seeing both a loss and a page event. The heartbeat keeps
    // running, so a later genuine claim reacquires and loads fresh.
    holding.value = false;
    if (!disposed && lineageId !== null) {
      deps.onPageHidden();
      heartbeat.start();
    }
  }

  const hasWindow = typeof window !== "undefined";
  if (hasWindow) {
    window.addEventListener("pagehide", handlePagehide);
  }

  onScopeDispose(() => {
    disposed = true;
    acquisition.stopWaiting();
    heartbeat.stop();
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
    isOpenClaimPending: () => acquisition.isClaimPending(),
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
