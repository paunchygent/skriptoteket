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
 *   work is tied to an identity (the lineage plus an acquisition epoch
 *   bumped on every open, lineage switch, dispose and `pagehide`): the
 *   identity is rechecked after every await before holding changes, a late
 *   successful old-lineage claim is released, and cancelling wakes a
 *   sleeping takeover poll so `requestTakeover` always settles.
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

import { computed, onScopeDispose, ref, watch } from "vue";

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
import { createTakeoverPoll } from "./examWorkspaceEditLeaseTakeover";
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
  /** Store the pending edit before yielding to a takeover. */
  onTakeoverRequested: () => Promise<void> | void;
  /** Read the newest state after claiming the lease. */
  onAcquired: () => Promise<void> | void;
};

export function useExamWorkspaceEditLease(deps: ExamWorkspaceEditLeaseDeps) {
  const tabId = deps.tabId ?? createExamWorkspaceEditLeaseTabId();
  const guest = deps.isGuest();
  const holding = ref(false);
  const waiting = ref(false);
  const readOnly = computed(() => !holding.value);
  let disposed = false;
  let driver: ExamWorkspaceEditLeaseDriver | null = null;
  let heartbeat: ReturnType<typeof setInterval> | null = null;
  const takeoverPoll = createTakeoverPoll(EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
  const clock = deps.now ?? (() => Date.now());
  let lastLeaseSuccessAt = clock();
  // The acquisition identity: the lineage plus an epoch bumped on every
  // open, lineage switch, dispose and `pagehide`. Async claim/takeover work
  // captures the epoch before awaiting and rechecks it after, so a late
  // result for an old identity is released instead of granting editability.
  let acquisitionEpoch = 0;
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

  function stopWaiting(): void {
    waiting.value = false;
    // Wake a sleeping takeover poll so `requestTakeover` settles on
    // cancellation instead of staying pending forever.
    takeoverPoll.cancel();
  }

  function noteLostLease(): void {
    // A yielded or refused tab stays read-only but keeps the heartbeat: the
    // next ticks retry the claim at the heartbeat cadence and take the lease
    // back as soon as it is free, exactly like a tab that opened read-only.
    // Only dispose, the lineage switch and `pagehide` stop the heartbeat.
    holding.value = false;
  }

  async function tryRelease(lineageId: string, keepalive = false): Promise<void> {
    if (driver === null) {
      return;
    }
    try {
      // Only the `pagehide` release carries options, so the recorded calls
      // of every other release keep their two-argument shape.
      if (keepalive) {
        await driver.release(lineageId, { keepalive: true });
      } else {
        await driver.release(lineageId);
      }
    } catch {
      // Best effort: closing and yielding never fail the session.
    }
  }

  /** Turn read-only and restart the heartbeat after yielding to a takeover. */
  function noteYielded(): void {
    noteLostLease();
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
    const tickEpoch = acquisitionEpoch;
    // A read-only tab retries its refused claim at the heartbeat cadence and
    // takes the lease as soon as it is free, with no `Ta över`. A waiting
    // takeover claims on its own faster poll instead. A `failed` retry claim
    // stays read-only; only the claim on open stays editable on such a
    // failure.
    if (!holding.value) {
      if (waiting.value) {
        return;
      }
      let outcome: "held" | "readonly" | "failed";
      try {
        outcome = await active.claim(lineageId);
      } catch {
        return;
      }
      if (disposed || acquisitionEpoch !== tickEpoch || deps.lineageId() !== lineageId || holding.value) {
        if (outcome === "held") {
          await tryRelease(lineageId);
        }
        return;
      }
      if (outcome === "held") {
        await noteAcquired(lineageId, tickEpoch);
      }
      return;
    }
    // The local deadline is enforced before awaiting: a holder whose last
    // success is past the TTL turns read-only even while a renew is still
    // pending. The next ticks then retry the claim at the heartbeat cadence.
    if (clock() - lastLeaseSuccessAt >= EXAM_WORKSPACE_EDIT_LEASE_TTL_MS) {
      noteLostLease();
      return;
    }
    const seq = renewSeq + 1;
    renewSeq = seq;
    const sentAt = clock();
    let renewed: "held" | "lost" | "failed";
    try {
      renewed = await active.renew(lineageId);
    } catch {
      renewed = "failed";
    }
    // In-flight renews settle in order: a result older than one already
    // applied is ignored, so an earlier success cannot overwrite a later
    // loss.
    if (seq <= appliedRenewSeq) {
      return;
    }
    appliedRenewSeq = seq;
    if (disposed || acquisitionEpoch !== tickEpoch || deps.lineageId() !== lineageId) {
      return;
    }
    if (renewed === "held") {
      // A late success never revives a lease that was lost or expired while
      // it was in flight, and it extends the deadline only from the time its
      // request was sent, never from the receipt time.
      if (!holding.value || clock() - sentAt >= EXAM_WORKSPACE_EDIT_LEASE_TTL_MS) {
        noteLostLease();
        return;
      }
      lastLeaseSuccessAt = sentAt;
      holding.value = true;
    } else if (renewed === "lost") {
      holding.value = false;
    } else if (clock() - lastLeaseSuccessAt >= EXAM_WORKSPACE_EDIT_LEASE_TTL_MS) {
      // Renewals kept failing past the lease TTL, so the server lease is
      // dead: turn read-only. The next ticks retry the claim and take the
      // lease back as soon as it is free.
      noteLostLease();
    }
    // A lost lease keeps the heartbeat: the next tick retries the claim and
    // takes the lease back as soon as it is free.
  }

  async function claimCurrent(lineageId: string): Promise<void> {
    const openEpoch = acquisitionEpoch;
    const active = ensureDriver();
    if (active === null) {
      holding.value = true;
      return;
    }
    let outcome: "held" | "readonly";
    try {
      const claimed = await active.claim(lineageId);
      // Only the claim on open stays editable on a failure that is not a
      // live foreign lease; every retry claim maps `failed` to read-only.
      outcome = claimed === "failed" ? "held" : claimed;
    } catch {
      outcome = "held";
    }
    if (disposed || acquisitionEpoch !== openEpoch || deps.lineageId() !== lineageId) {
      if (outcome === "held") {
        await tryRelease(lineageId);
      }
      return;
    }
    holding.value = outcome === "held";
    if (holding.value) {
      lastLeaseSuccessAt = clock();
    }
    // The heartbeat both renews a held lease and retries a refused claim, so
    // a reloaded tab takes the lease as soon as it is free, with no `Ta över`.
    startHeartbeat();
  }

  async function noteAcquired(lineageId: string, epoch: number): Promise<void> {
    // Guarded before mutating shared state: a late success for an old
    // identity is released and changes nothing.
    if (disposed || acquisitionEpoch !== epoch || deps.lineageId() !== lineageId) {
      await tryRelease(lineageId);
      return;
    }
    lastLeaseSuccessAt = clock();
    holding.value = true;
    stopWaiting();
    startHeartbeat();
    await deps.onAcquired();
  }

  /**
   * `Ta över`: record the request, claim at once when the lease is already
   * free, else poll the claim until the holder releases or its lease dies,
   * then read the newest state. While waiting the tab stays read-only.
   */
  async function requestTakeover(): Promise<void> {
    const lineageId = deps.lineageId();
    const active = ensureDriver();
    if (lineageId === null || active === null || holding.value || waiting.value || disposed) {
      return;
    }
    const takeoverEpoch = acquisitionEpoch;
    const isCurrent = (): boolean =>
      !disposed && acquisitionEpoch === takeoverEpoch && deps.lineageId() === lineageId;
    waiting.value = true;
    try {
      await takeoverPoll.run(active, lineageId, {
        isCurrent,
        noteAcquired: (acquiredLineage: string) => noteAcquired(acquiredLineage, takeoverEpoch),
        noteOwn: () => {
          lastLeaseSuccessAt = clock();
          holding.value = true;
          stopWaiting();
          startHeartbeat();
        },
        release: (staleLineage: string) => tryRelease(staleLineage),
        shouldWait: () => waiting.value && !holding.value,
      });
    } finally {
      if (!holding.value) {
        stopWaiting();
      }
    }
  }

  function handlePagehide(): void {
    const lineageId = deps.lineageId();
    acquisitionEpoch += 1;
    stopWaiting();
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

  watch(
    () => deps.lineageId(),
    (next, previous) => {
      // A new identity: in-flight work for the old lineage is stale and
      // must be released instead of granting editability.
      acquisitionEpoch += 1;
      stopWaiting();
      if (previous !== null && previous !== undefined && holding.value) {
        const active = ensureDriver();
        if (active !== null) {
          void tryRelease(previous);
        }
      }
      holding.value = false;
      stopHeartbeat();
      if (next !== null && !disposed) {
        void claimCurrent(next);
      }
    },
    { immediate: true },
  );

  onScopeDispose(() => {
    disposed = true;
    acquisitionEpoch += 1;
    stopWaiting();
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
    readOnly,
    requestTakeover,
    /** The tab id this page load writes with. */
    tabId,
    /** True while `Ta över` waits for the holder to release. */
    waiting: computed(() => waiting.value),
  };
}
