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
  const open = (tabId: string, events: { flushed: string[]; acquired: string[] }) => {
    const scope = effectScope();
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        guestStorage: storage,
        isGuest: () => true,
        lineageId: () => LINEAGE,
        now,
        onAcquired: () => void events.acquired.push("reloaded"),
        onTakeoverRequested: () => void events.flushed.push("stored"),
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
