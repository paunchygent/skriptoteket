/**
 * Guest exam workspace edit lease.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour items 7 and 8, unit K7):
 *   One tab at a time edits a guest exam. Opening the exam claims the lease;
 *   the claim fails while another tab holds a live lease. The holder renews
 *   every 5 s and a lease not renewed for 15 s is dead, so a waiting tab can
 *   claim it. `Ta över` asks for the lease: the holder stores its pending
 *   edit and releases, and the takeover is immediate between tabs through a
 *   `BroadcastChannel`. A closed tab releases on `pagehide`.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createGuestEditLeaseController,
  createInMemoryGuestEditLeaseStorage,
  GUEST_EDIT_LEASE_HEARTBEAT_MS,
  GUEST_EDIT_LEASE_TTL_MS,
  type GuestEditLeaseChannel,
  type GuestEditLeaseMessage,
} from "./examWorkspaceGuestEditLease";

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

function setup() {
  const storage = createInMemoryGuestEditLeaseStorage();
  const hub = createChannelHub();
  let nowMs = 1_000_000;
  const now = () => nowMs;
  const advance = (ms: number) => {
    nowMs += ms;
  };
  const holder = (onTakeoverRequested: () => Promise<void> | void = () => undefined) =>
    createGuestEditLeaseController({
      now,
      onTakeoverRequested,
      openChannel: () => hub.createChannel(),
      storage,
      tabId: `tab-${Math.random().toString(16).slice(2)}`,
    });
  return { advance, holder, hub, now, storage };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("examWorkspaceGuestEditLease", () => {
  it("names the 5 s heartbeat and the 15 s lease death", () => {
    expect(GUEST_EDIT_LEASE_HEARTBEAT_MS).toBe(5_000);
    expect(GUEST_EDIT_LEASE_TTL_MS).toBe(15_000);
  });

  it("refuses a second claim while the holder renews, then grants it after 15 s without renewal", async () => {
    vi.useFakeTimers();
    const context = setup();
    const first = context.holder();
    const second = context.holder();
    try {
      expect(await first.claim()).toBe("held");
      expect(await second.claim()).toBe("readonly");

      await vi.advanceTimersByTimeAsync(GUEST_EDIT_LEASE_HEARTBEAT_MS * 2);
      expect(await second.claim()).toBe("readonly");

      // The first tab crashes: its heartbeat stops but the record stays.
      first.dispose();
      context.advance(GUEST_EDIT_LEASE_TTL_MS + 1);
      expect(await second.claim()).toBe("held");
    } finally {
      first.dispose();
      second.dispose();
    }
  });

  it("answers a takeover request by storing the pending edit and releasing", async () => {
    const context = setup();
    const first = context.holder();
    const second = context.holder();
    const seen: string[] = [];
    const releasable = context.holder(async () => {
      seen.push("stored");
    });
    try {
      expect(await releasable.claim()).toBe("held");

      const events: string[] = [];
      const unobserve = second.observe((event) => {
        events.push(event.kind);
      });
      try {
        expect(await second.requestTakeover()).toBe("requested");
        for (let attempt = 0; attempt < 20; attempt += 1) {
          if ((await context.storage.load()) === null) {
            break;
          }
          await Promise.resolve();
        }

        expect(seen).toEqual(["stored"]);
        expect(await context.storage.load()).toBeNull();
        expect(events).toContain("lease-released");
        expect(await second.claim()).toBe("held");
      } finally {
        unobserve();
      }
    } finally {
      first.dispose();
      second.dispose();
      releasable.dispose();
    }
  });

  it("claims at once when no lease or only a dead one is stored", async () => {
    const context = setup();
    const first = context.holder();
    const second = context.holder();
    try {
      expect(await first.requestTakeover()).toBe("claimed");
      expect(await first.requestTakeover()).toBe("own");

      first.dispose();
      context.advance(GUEST_EDIT_LEASE_TTL_MS + 1);
      expect(await second.requestTakeover()).toBe("claimed");
    } finally {
      first.dispose();
      second.dispose();
    }
  });

  it("releases on pagehide so a waiting tab can claim at once", async () => {
    const context = setup();
    const first = context.holder();
    const second = context.holder();
    try {
      expect(await first.claim()).toBe("held");

      window.dispatchEvent(new Event("pagehide"));
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if ((await context.storage.load()) === null) {
          break;
        }
        await Promise.resolve();
      }

      expect(await context.storage.load()).toBeNull();
      expect(await second.claim()).toBe("held");
    } finally {
      first.dispose();
      second.dispose();
    }
  });
});
