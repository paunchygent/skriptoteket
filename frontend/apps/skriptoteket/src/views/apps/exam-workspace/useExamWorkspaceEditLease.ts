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
 *   (expired or released) with no `Ta över`; any
 *   other claim failure stays editable, since the write guard is
 *   authoritative and refuses a tab without the lease.
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
  let takeoverTimer: ReturnType<typeof setTimeout> | null = null;

  function stopHeartbeat(): void {
    if (heartbeat !== null) {
      clearInterval(heartbeat);
      heartbeat = null;
    }
  }

  function stopWaiting(): void {
    waiting.value = false;
    if (takeoverTimer !== null) {
      clearTimeout(takeoverTimer);
      takeoverTimer = null;
    }
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

  /** Store the pending edit, release and turn read-only for the waiting tab. */
  async function yieldLease(lineageId: string): Promise<void> {
    try {
      await deps.onTakeoverRequested();
    } finally {
      await tryRelease(lineageId);
      noteLostLease();
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
    // takeover claims on its own faster poll instead.
    if (!holding.value) {
      if (waiting.value) {
        return;
      }
      let outcome: "held" | "readonly";
      try {
        outcome = await active.claim(lineageId);
      } catch {
        return;
      }
      if (disposed || deps.lineageId() !== lineageId || holding.value) {
        return;
      }
      if (outcome === "held") {
        await noteAcquired(lineageId);
      }
      return;
    }
    let held: boolean;
    try {
      held = await active.renew(lineageId);
    } catch {
      return;
    }
    if (disposed || deps.lineageId() !== lineageId) {
      return;
    }
    holding.value = held;
    // A lost lease keeps the heartbeat: the next tick retries the claim and
    // takes the lease back as soon as it is free.
  }

  async function claimCurrent(lineageId: string): Promise<void> {
    const active = ensureDriver();
    if (active === null) {
      holding.value = true;
      return;
    }
    let outcome: "held" | "readonly";
    try {
      outcome = await active.claim(lineageId);
    } catch {
      outcome = "held";
    }
    if (disposed || deps.lineageId() !== lineageId) {
      if (outcome === "held") {
        await tryRelease(lineageId);
      }
      return;
    }
    holding.value = outcome === "held";
    // The heartbeat both renews a held lease and retries a refused claim, so
    // a reloaded tab takes the lease as soon as it is free, with no `Ta över`.
    startHeartbeat();
  }

  async function noteAcquired(lineageId: string): Promise<void> {
    holding.value = true;
    stopWaiting();
    startHeartbeat();
    if (!disposed && deps.lineageId() === lineageId) {
      await deps.onAcquired();
    }
  }

  function sleepTakeoverPoll(): Promise<void> {
    return new Promise<void>((resolve) => {
      takeoverTimer = setTimeout(() => {
        takeoverTimer = null;
        resolve();
      }, EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
    });
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
    waiting.value = true;
    try {
      let outcome: "claimed" | "requested" | "own";
      try {
        outcome = await active.requestTakeover(lineageId);
      } catch {
        outcome = "requested";
      }
      if (disposed || deps.lineageId() !== lineageId) {
        return;
      }
      if (outcome === "own") {
        holding.value = true;
        stopWaiting();
        startHeartbeat();
        return;
      }
      if (outcome === "claimed") {
        await noteAcquired(lineageId);
        return;
      }
      while (!disposed && waiting.value && deps.lineageId() === lineageId && !holding.value) {
        await sleepTakeoverPoll();
        if (disposed || !waiting.value || deps.lineageId() !== lineageId) {
          return;
        }
        let next: "held" | "readonly";
        try {
          next = await active.claim(lineageId);
        } catch {
          continue;
        }
        if (next === "held") {
          await noteAcquired(lineageId);
          return;
        }
      }
    } finally {
      if (!holding.value) {
        stopWaiting();
      }
    }
  }

  function handlePagehide(): void {
    const lineageId = deps.lineageId();
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
