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

  it("lets exactly one tab edit when two tabs claim the free slot at the same time", async () => {
    const context = setup();
    const first = context.holder();
    const second = context.holder();
    try {
      const outcomes = await Promise.all([first.claim(), second.claim()]);

      expect(outcomes.filter((outcome) => outcome === "held")).toHaveLength(1);
      const stored = await context.storage.load();
      expect(stored === null ? null : stored.tabId).toBe(
        outcomes[0] === "held" ? first.tabId : second.tabId,
      );
    } finally {
      first.dispose();
      second.dispose();
    }
  });

  it("does not let a stale renew or release overwrite the tab that took the lease", async () => {
    const context = setup();
    const first = context.holder();
    const second = context.holder();
    try {
      expect(await first.claim()).toBe("held");

      // The second tab takes over fully and claims the freed lease.
      expect(await second.requestTakeover()).toBe("requested");
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if ((await context.storage.load()) === null) {
          break;
        }
        await Promise.resolve();
      }
      expect(await second.claim()).toBe("held");

      // The first tab lost the lease: its renewal and release report false
      // and leave the new owner's record alone.
      expect(await first.renew()).toBe(false);
      expect(await context.storage.load()).toMatchObject({ tabId: second.tabId });
      expect(await first.release()).toBe(false);
      expect(await context.storage.load()).toMatchObject({ tabId: second.tabId });
    } finally {
      first.dispose();
      second.dispose();
    }
  });

  it("decides each lease step atomically on one shared slot", async () => {
    const storage = createInMemoryGuestEditLeaseStorage();
    const at = 1_000_000;

    const free = await storage.claim("tab-a", at);
    expect(free).toEqual({
      held: true,
      record: { renewedAt: at, tabId: "tab-a", takeoverRequestedBy: null },
    });

    const refused = await storage.claim("tab-b", at + 1_000);
    expect(refused.held).toBe(false);
    expect(refused.record).toMatchObject({ tabId: "tab-a" });

    const renewed = await storage.renew("tab-a", at + 2_000);
    expect(renewed).toEqual({
      held: true,
      record: { renewedAt: at + 2_000, tabId: "tab-a", takeoverRequestedBy: null },
    });
    expect(await storage.renew("tab-b", at + 2_000)).toEqual({
      held: false,
      record: { renewedAt: at + 2_000, tabId: "tab-a", takeoverRequestedBy: null },
    });

    const asked = await storage.requestTakeover("tab-b", at + 3_000);
    expect(asked.outcome).toBe("requested");
    expect(asked.record).toMatchObject({ tabId: "tab-a", takeoverRequestedBy: "tab-b" });

    // A renewal paused by a waiting ask does not move the renewal forward.
    expect(await storage.renew("tab-a", at + 4_000)).toEqual({
      held: false,
      record: { renewedAt: at + 2_000, tabId: "tab-a", takeoverRequestedBy: "tab-b" },
    });

    expect(await storage.requestTakeover("tab-a", at + 4_000)).toEqual({
      outcome: "own",
      record: { renewedAt: at + 2_000, tabId: "tab-a", takeoverRequestedBy: "tab-b" },
    });
    expect(await storage.release("tab-b")).toBe(false);
    expect(await storage.release("tab-a")).toBe(true);
    expect(await storage.load()).toBeNull();

    // An expired lease is taken at once, clearing the old ask.
    const expiredAt = at + GUEST_EDIT_LEASE_TTL_MS + 1;
    expect(await storage.claim("tab-a", at)).toBeDefined();
    const taken = await storage.requestTakeover("tab-b", expiredAt);
    expect(taken.outcome).toBe("claimed");
    expect(taken.record).toEqual({
      renewedAt: expiredAt,
      tabId: "tab-b",
      takeoverRequestedBy: null,
    });
  });
});
