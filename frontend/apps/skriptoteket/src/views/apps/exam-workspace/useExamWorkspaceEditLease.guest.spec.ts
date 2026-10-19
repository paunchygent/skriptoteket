/**
 * Exam workspace edit lease: one editing tab on the guest lease.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour items 7 and 8, decision
 * D5, unit K8):
 *   A guest's tabs share one lease record in the same IndexedDB database as
 *   the draft. A second tab opens read-only. `Ta över` requests the lease:
 *   the holder stores its pending edit, releases and turns read-only, and
 *   the waiting tab claims it and reads the newest state. After 15 s without
 *   renewal the lease is dead and a waiting tab claims it. A closed tab
 *   releases its lease on `pagehide`.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createInMemoryGuestEditLeaseStorage,
  type GuestEditLeaseChannel,
  type GuestEditLeaseMessage,
  type GuestEditLeaseStoragePort,
} from "./examWorkspaceGuestEditLease";
import {
  EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS,
  useExamWorkspaceEditLease,
} from "./useExamWorkspaceEditLease";

const LINEAGE = "00000000-0000-4000-8000-000000000001";

type ChannelListener = (event: { data: GuestEditLeaseMessage }) => void;

/** A BroadcastChannel double: every channel on the hub hears the others at once. */
function createChannelHub() {
  const endpoints = new Set<{ listeners: Set<ChannelListener>; closed: boolean }>();
  return {
    createChannel(): GuestEditLeaseChannel {
      const endpoint = { closed: false, listeners: new Set<ChannelListener>() };
      endpoints.add(endpoint);
      return {
        addEventListener(type, listener) {
          if (type === "message") {
            endpoint.listeners.add(listener);
          }
        },
        close() {
          endpoint.closed = true;
          endpoints.delete(endpoint);
        },
        postMessage(message) {
          for (const other of endpoints) {
            if (other !== endpoint && !other.closed) {
              for (const listener of [...other.listeners]) {
                listener({ data: message });
              }
            }
          }
        },
        removeEventListener(type, listener) {
          if (type === "message") {
            endpoint.listeners.delete(listener);
          }
        },
      };
    },
  };
}

function setupGuestLeases() {
  const storage: GuestEditLeaseStoragePort = createInMemoryGuestEditLeaseStorage();
  const hub = createChannelHub();
  let nowMs = 1_000_000;
  const now = () => nowMs;
  const advance = (ms: number) => {
    nowMs += ms;
  };
  const open = (
    tabId: string,
    events: { flushed: string[]; acquired: string[] },
    overrides?: {
      guestStorage?: GuestEditLeaseStoragePort;
      onTakeoverRequested?: () => Promise<void> | void;
    },
  ) => {
    const scope = effectScope();
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        guestStorage: overrides?.guestStorage ?? storage,
        isGuest: () => true,
        lineageId: () => LINEAGE,
        now,
        onAcquired: () => void events.acquired.push("reloaded"),
        onTakeoverRequested:
          overrides?.onTakeoverRequested ?? (() => void events.flushed.push("stored")),
        openGuestChannel: () => hub.createChannel(),
        tabId,
      }),
    )!;
    return { lease, stop: () => scope.stop() };
  };
  return { advance, open, storage };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

/** Count one tab's atomic lease decisions against the shared slot. */
function wrapCountingLeaseStorage(
  inner: GuestEditLeaseStoragePort,
  counter: { claims: number },
): GuestEditLeaseStoragePort {
  return {
    claim: async (...args) => {
      counter.claims += 1;
      return inner.claim(...args);
    },
    load: (...args) => inner.load(...args),
    release: (...args) => inner.release(...args),
    renew: (...args) => inner.renew(...args),
    requestTakeover: (...args) => inner.requestTakeover(...args),
  };
}

describe("useExamWorkspaceEditLease on the guest lease", () => {
  it("opens the second tab read-only while the first holds the lease", async () => {
    const context = setupGuestLeases();
    const firstEvents = { acquired: [] as string[], flushed: [] as string[] };
    const secondEvents = { acquired: [] as string[], flushed: [] as string[] };
    const first = context.open("tab-a", firstEvents);
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      expect(second.lease.readOnly.value).toBe(true);
      expect(await context.storage.load()).toMatchObject({ tabId: "tab-a" });
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("hands the lease over on Ta över: the holder stores first, the waiter reloads", async () => {
    const context = setupGuestLeases();
    const firstEvents = { acquired: [] as string[], flushed: [] as string[] };
    const secondEvents = { acquired: [] as string[], flushed: [] as string[] };
    const first = context.open("tab-a", firstEvents);
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      const taking = second.lease.requestTakeover();
      await flushPromises();
      expect(firstEvents.flushed).toEqual(["stored"]);
      await vi.advanceTimersByTimeAsync(1_000);
      await taking;
      expect(first.lease.readOnly.value).toBe(true);
      expect(second.lease.readOnly.value).toBe(false);
      expect(secondEvents.acquired).toEqual(["reloaded"]);
      expect(await context.storage.load()).toMatchObject({ tabId: "tab-b" });
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("takes the lease back on the next heartbeat after yielding it", async () => {
    const context = setupGuestLeases();
    const firstEvents: { acquired: string[]; flushed: string[] } = { acquired: [], flushed: [] };
    const secondEvents: { acquired: string[]; flushed: string[] } = { acquired: [], flushed: [] };
    const first = context.open("tab-a", firstEvents);
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      const taking = second.lease.requestTakeover();
      await flushPromises();
      expect(firstEvents.flushed).toEqual(["stored"]);
      await vi.advanceTimersByTimeAsync(1_000);
      await taking;
      expect(first.lease.readOnly.value).toBe(true);
      expect(second.lease.readOnly.value).toBe(false);

      // The taking tab closes: its dispose release frees the lease.
      second.stop();
      for (let attempt = 0; attempt < 20; attempt += 1) {
        const loaded = await context.storage.load();
        if (loaded === null) {
          break;
        }
        await Promise.resolve();
      }
      expect(await context.storage.load()).toBeNull();

      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(await context.storage.load()).toMatchObject({ tabId: "tab-a" });
      expect(first.lease.readOnly.value).toBe(false);
      expect(firstEvents.acquired).toEqual(["reloaded"]);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("waits one full heartbeat after a yield before claiming again, letting the waiter take over", async () => {
    const context = setupGuestLeases();
    const firstEvents: { acquired: string[]; flushed: string[] } = { acquired: [], flushed: [] };
    const secondEvents: { acquired: string[]; flushed: string[] } = { acquired: [], flushed: [] };
    const firstCounter = { claims: 0 };
    let delayTakeoverFlush = true;
    let releaseStore: () => void = () => undefined;
    const first = context.open("tab-a", firstEvents, {
      guestStorage: wrapCountingLeaseStorage(context.storage, firstCounter),
      onTakeoverRequested: () => {
        if (delayTakeoverFlush) {
          delayTakeoverFlush = false;
          return new Promise<void>((resolve) => {
            releaseStore = () => {
              firstEvents.flushed.push("stored");
              resolve();
            };
          });
        }
        firstEvents.flushed.push("stored");
        return undefined;
      },
    });
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      expect(second.lease.readOnly.value).toBe(true);
      const taking = second.lease.requestTakeover();
      await flushPromises();

      // The holder's answer resolves just before its old heartbeat phase
      // would fire again; the release lands on a fresh phase.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS - 100);
      releaseStore();
      await flushPromises();
      expect(firstEvents.flushed).toEqual(["stored"]);
      expect(first.lease.readOnly.value).toBe(true);
      expect(await context.storage.load()).toBeNull();
      const claimsAfterYield = firstCounter.claims;

      // 200 ms later the old phase would already have fired: the yielded tab
      // must still have sent no claim, while the waiter's poll takes the lease.
      // (Assert before awaiting the takeover: on the old phase the yielded
      // tab reclaims first and the waiter never resolves here.)
      await vi.advanceTimersByTimeAsync(200);
      expect(firstCounter.claims).toBe(claimsAfterYield);
      await taking;
      expect(await context.storage.load()).toMatchObject({ tabId: "tab-b" });
      expect(second.lease.readOnly.value).toBe(false);
      expect(secondEvents.acquired).toEqual(["reloaded"]);
      expect(first.lease.readOnly.value).toBe(true);

      // One full heartbeat after the release the yielded tab retries once and
      // is refused, staying read-only without a reload.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(firstCounter.claims).toBe(claimsAfterYield + 1);
      expect(await context.storage.load()).toMatchObject({ tabId: "tab-b" });
      expect(first.lease.readOnly.value).toBe(true);
      expect(firstEvents.acquired).toEqual([]);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("keeps the heartbeat phase after a refused write", async () => {
    const context = setupGuestLeases();
    const firstEvents = { acquired: [] as string[], flushed: [] as string[] };
    const secondEvents = { acquired: [] as string[], flushed: [] as string[] };
    const first = context.open("tab-a", firstEvents);
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      expect(second.lease.readOnly.value).toBe(true);

      // A refused write turns the tab read-only but keeps the heartbeat
      // phase: the next tick still fires on the old phase.
      await vi.advanceTimersByTimeAsync(1_000);
      second.lease.noteLostLease();
      expect(second.lease.readOnly.value).toBe(true);

      // The holder goes away: its dispose release frees the lease.
      first.stop();
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if ((await context.storage.load()) === null) {
          break;
        }
        await Promise.resolve();
      }
      expect(await context.storage.load()).toBeNull();

      // The next tick on the kept phase claims the freed lease at once.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS - 1_000);
      expect(await context.storage.load()).toMatchObject({ tabId: "tab-b" });
      expect(second.lease.readOnly.value).toBe(false);
      expect(secondEvents.acquired).toEqual(["reloaded"]);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("lets a waiting tab claim after 15 s without renewal", async () => {
    const context = setupGuestLeases();
    const firstEvents = { acquired: [] as string[], flushed: [] as string[] };
    const secondEvents = { acquired: [] as string[], flushed: [] as string[] };
    const first = context.open("tab-a", firstEvents);
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      expect(second.lease.readOnly.value).toBe(true);
      // The first tab crashes: its heartbeat stops firing but the record stays.
      context.advance(15_001);

      const taking = second.lease.requestTakeover();
      await taking;
      expect(second.lease.readOnly.value).toBe(false);
      expect(secondEvents.acquired).toEqual(["reloaded"]);

      // The stale holder's next heartbeat finds the lease lost.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(first.lease.readOnly.value).toBe(true);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("renews the guest lease every 5 s while holding", async () => {
    const context = setupGuestLeases();
    const firstEvents = { acquired: [] as string[], flushed: [] as string[] };
    const first = context.open("tab-a", firstEvents);
    try {
      await flushPromises();
      const before = (await context.storage.load())!.renewedAt;
      context.advance(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect((await context.storage.load())!.renewedAt).toBeGreaterThan(before);
      expect(first.lease.readOnly.value).toBe(false);
    } finally {
      first.stop();
    }
  });

  it("releases on pagehide so a waiting tab claims at once", async () => {
    const context = setupGuestLeases();
    const firstEvents = { acquired: [] as string[], flushed: [] as string[] };
    const secondEvents = { acquired: [] as string[], flushed: [] as string[] };
    const first = context.open("tab-a", firstEvents);
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      window.dispatchEvent(new Event("pagehide"));
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if ((await context.storage.load()) === null) {
          break;
        }
        await Promise.resolve();
      }
      expect(await context.storage.load()).toBeNull();

      const taking = second.lease.requestTakeover();
      await taking;
      expect(second.lease.readOnly.value).toBe(false);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("retries a refused claim and takes the freed lease without Ta över", async () => {
    const context = setupGuestLeases();
    const firstEvents = { acquired: [] as string[], flushed: [] as string[] };
    const secondEvents = { acquired: [] as string[], flushed: [] as string[] };
    const first = context.open("tab-a", firstEvents);
    await flushPromises();
    const second = context.open("tab-b", secondEvents);
    try {
      await flushPromises();
      expect(second.lease.readOnly.value).toBe(true);
      // The only tab reloads: its pagehide release frees the lease, and the
      // reloaded tab reclaims it on its next retry, not on Ta över.
      window.dispatchEvent(new Event("pagehide"));
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if ((await context.storage.load()) === null) {
          break;
        }
        await Promise.resolve();
      }
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(await context.storage.load()).toMatchObject({ tabId: "tab-b" });
      expect(second.lease.readOnly.value).toBe(false);
      expect(secondEvents.acquired).toEqual(["reloaded"]);
    } finally {
      first.stop();
      second.stop();
    }
  });
});
