/**
 * Exam workspace edit lease: one editing tab on the server lease.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit K8):
 *   One random tab id per page load; claim on opening an exam, renew every
 *   5 s, and a lease not renewed for 15 s is dead. A second tab opens
 *   read-only. The holder sees a takeover request at its next renew, stores
 *   its pending edit, releases and turns read-only. `Ta över` requests the
 *   lease and claims it once the holder has released or its lease has
 *   expired, then reads the newest state. A lost lease at renew turns
 *   read-only without a reload. `pagehide` releases. A claim refused with
 *   `EDIT_LEASE_HELD` opens read-only; any other claim failure stays
 *   editable, since the write guard is authoritative.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
import {
  createExamWorkspaceEditLeaseTabId,
  EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS,
  EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS,
  EXAM_WORKSPACE_EDIT_LEASE_TTL_MS,
  useExamWorkspaceEditLease,
  type ExamWorkspaceEditLeaseServer,
} from "./useExamWorkspaceEditLease";

const LINEAGE = "00000000-0000-4000-8000-000000000001";
const OTHER_LINEAGE = "00000000-0000-4000-8000-000000000002";

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "Provet redigeras i en annan flik.", status: 409 });
}

/** A lease server with the K6 semantics and a test-controlled clock. */
function createFakeLeaseServer() {
  let nowMs = 1_000_000;
  let holder: string | null = null;
  let renewedAt = 0;
  let waiting: string | null = null;
  const live = () => holder !== null && nowMs - renewedAt < EXAM_WORKSPACE_EDIT_LEASE_TTL_MS;
  const response = (forTab: string): ExamWorkspaceEditLeaseResponse => ({
    holder_tab_id: holder,
    renewed_at: new Date(renewedAt).toISOString(),
    takeover_requested: waiting !== null && waiting !== forTab,
    takeover_requested_by: waiting,
  });
  const server: ExamWorkspaceEditLeaseServer = {
    async claim(_lineage: string, tabId: string) {
      if (live() && holder !== tabId) {
        throw heldError();
      }
      holder = tabId;
      renewedAt = nowMs;
      if (waiting === tabId) {
        waiting = null;
      }
      return response(tabId);
    },
    async renew(_lineage: string, tabId: string) {
      if (!live() || holder !== tabId) {
        throw heldError();
      }
      renewedAt = nowMs;
      return response(tabId);
    },
    async requestTakeover(_lineage: string, tabId: string) {
      if (holder === tabId) {
        return response(tabId);
      }
      waiting = tabId;
      return response(tabId);
    },
    async release(_lineage: string, tabId: string) {
      if (!live() || holder !== tabId) {
        throw heldError();
      }
      holder = null;
      renewedAt = 0;
      return response(tabId);
    },
  };
  return {
    advance: (ms: number) => {
      nowMs += ms;
    },
    server,
    state: () => ({ holder, waiting }),
  };
}

type LeaseSetup = {
  lineage: string | null;
  flushed: string[];
  acquired: string[];
  lease: ReturnType<typeof useExamWorkspaceEditLease>;
  stop: () => void;
};

function setupLease(
  fake: ReturnType<typeof createFakeLeaseServer>,
  options: { tabId: string; lineage?: string | null } & Partial<
    Pick<Parameters<typeof useExamWorkspaceEditLease>[0], "onAcquired" | "onTakeoverRequested">
  >,
): LeaseSetup {
  const scope = effectScope();
  const holder = { lineage: options.lineage ?? LINEAGE };
  const flushed: string[] = [];
  const acquired: string[] = [];
  const lease = scope.run(() =>
    useExamWorkspaceEditLease({
      lineageId: () => holder.lineage,
      isGuest: () => false,
      server: fake.server,
      tabId: options.tabId,
      onAcquired: options.onAcquired ?? (async () => {
        acquired.push("reloaded");
      }),
      onTakeoverRequested: options.onTakeoverRequested ?? (async () => {
        flushed.push("stored");
      }),
    }),
  )!;
  return {
    acquired,
    flushed,
    lease,
    lineage: holder.lineage,
    stop: () => scope.stop(),
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useExamWorkspaceEditLease on the server lease", () => {
  it("names the 5 s heartbeat and the 15 s lease death the server enforces", () => {
    expect(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS).toBe(5_000);
    expect(EXAM_WORKSPACE_EDIT_LEASE_TTL_MS).toBe(15_000);
  });

  it("hands every page load its own random tab id", () => {
    const first = createExamWorkspaceEditLeaseTabId();
    const second = createExamWorkspaceEditLeaseTabId();
    expect(first).not.toBe("");
    expect(first).not.toBe(second);
  });

  it("claims on open while a second tab opens read-only", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      expect(second.lease.readOnly.value).toBe(true);
      expect(fake.state().holder).toBe("tab-a");
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("renews the lease every 5 s while holding", async () => {
    const fake = createFakeLeaseServer();
    const renew = vi.spyOn(fake.server, "renew");
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(renew).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(renew).toHaveBeenCalledTimes(1);
      expect(renew).toHaveBeenCalledWith(LINEAGE, "tab-a");
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(renew).toHaveBeenCalledTimes(2);
    } finally {
      first.stop();
    }
  });

  it("stores the pending edit and releases when a takeover waits at renew", async () => {
    const fake = createFakeLeaseServer();
    const release = vi.spyOn(fake.server, "release");
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      const taking = second.lease.requestTakeover();
      await flushPromises();
      expect(fake.state().waiting).toBe("tab-b");

      await vi.advanceTimersByTimeAsync(4 * EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
      expect(fake.state().holder).toBe("tab-a");
      expect(first.flushed).toEqual([]);
      expect(first.lease.readOnly.value).toBe(false);
      expect(second.lease.readOnly.value).toBe(true);

      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(first.flushed).toEqual(["stored"]);
      expect(release).toHaveBeenCalledWith(LINEAGE, "tab-a");
      expect(first.lease.readOnly.value).toBe(true);

      await taking;
      expect(second.lease.readOnly.value).toBe(false);
      expect(second.acquired).toEqual(["reloaded"]);
      expect(fake.state().holder).toBe("tab-b");
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("turns read-only without a reload when renew finds the lease lost", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      fake.advance(EXAM_WORKSPACE_EDIT_LEASE_TTL_MS + 1);

      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(first.lease.readOnly.value).toBe(true);
      expect(first.flushed).toEqual([]);
      expect(first.acquired).toEqual([]);
    } finally {
      first.stop();
    }
  });

  it("claims after 15 s without renewal and the stale holder turns read-only", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      expect(second.lease.readOnly.value).toBe(true);
      fake.advance(EXAM_WORKSPACE_EDIT_LEASE_TTL_MS + 1);

      const taking = second.lease.requestTakeover();
      await taking;
      expect(second.lease.readOnly.value).toBe(false);
      expect(second.acquired).toEqual(["reloaded"]);

      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(first.lease.readOnly.value).toBe(true);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("releases on pagehide so a waiting tab claims at once", async () => {
    const fake = createFakeLeaseServer();
    const release = vi.spyOn(fake.server, "release");
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      window.dispatchEvent(new Event("pagehide"));
      await flushPromises();
      // The unload release must survive the page teardown, so it goes out
      // with `keepalive`; a plain fetch is cancelled and the lease lingers.
      expect(release).toHaveBeenCalledWith(LINEAGE, "tab-a", { keepalive: true });

      const taking = second.lease.requestTakeover();
      await taking;
      expect(second.lease.readOnly.value).toBe(false);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("retries a refused claim at the heartbeat and takes the freed lease without Ta över", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      expect(second.lease.readOnly.value).toBe(true);
      // The only tab reloads: its pagehide release frees the lease at once,
      // and the reloaded tab reclaims it on its next retry, not on Ta över.
      window.dispatchEvent(new Event("pagehide"));
      await flushPromises();
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(fake.state().holder).toBe("tab-b");
      expect(second.lease.readOnly.value).toBe(false);
      expect(second.acquired).toEqual(["reloaded"]);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("takes the lease after expiry without Ta över when the holder never releases", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      expect(second.lease.readOnly.value).toBe(true);
      // The holder crashes without releasing: the refused claim retries and
      // takes the dead lease once the 15 s TTL passes, with no Ta över.
      fake.advance(EXAM_WORKSPACE_EDIT_LEASE_TTL_MS + 1);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(fake.state().holder).toBe("tab-b");
      expect(second.lease.readOnly.value).toBe(false);
      expect(second.acquired).toEqual(["reloaded"]);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("opens read-only when the claim meets a live foreign lease", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      const second = setupLease(fake, { tabId: "tab-b" });
      try {
        await flushPromises();
        expect(second.lease.readOnly.value).toBe(true);
      } finally {
        second.stop();
      }
    } finally {
      first.stop();
    }
  });

  it("stays editable when the claim fails for any reason but a held lease", async () => {
    const failing: ExamWorkspaceEditLeaseServer = {
      claim: () => Promise.reject(new Error("offline")),
      release: () => Promise.reject(new Error("offline")),
      renew: () => Promise.reject(new Error("offline")),
      requestTakeover: () => Promise.reject(new Error("offline")),
    };
    const scope = effectScope();
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        isGuest: () => false,
        lineageId: () => LINEAGE,
        onAcquired: () => Promise.resolve(),
        onTakeoverRequested: () => Promise.resolve(),
        server: failing,
        tabId: "tab-a",
      }),
    )!;
    try {
      await flushPromises();
      expect(lease.readOnly.value).toBe(false);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(lease.readOnly.value).toBe(false);
    } finally {
      scope.stop();
    }
  });

  it("turns read-only when told the lease is lost, keeping the pending edit", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      first.lease.noteLostLease();
      expect(first.lease.readOnly.value).toBe(true);
      expect(first.flushed).toEqual([]);
      expect(first.acquired).toEqual([]);
    } finally {
      first.stop();
    }
  });

  it("releases the old exam and claims the new one when the lineage changes", async () => {
    const fake = createFakeLeaseServer();
    const release = vi.spyOn(fake.server, "release");
    const claim = vi.spyOn(fake.server, "claim");
    const scope = effectScope();
    const lineage = ref<string | null>(LINEAGE);
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        isGuest: () => false,
        lineageId: () => lineage.value,
        onAcquired: () => Promise.resolve(),
        onTakeoverRequested: () => Promise.resolve(),
        server: fake.server,
        tabId: "tab-a",
      }),
    )!;
    try {
      await flushPromises();
      expect(lease.readOnly.value).toBe(false);
      lineage.value = OTHER_LINEAGE;
      await flushPromises();
      expect(release).toHaveBeenCalledWith(LINEAGE, "tab-a");
      expect(claim).toHaveBeenCalledWith(OTHER_LINEAGE, "tab-a");
      expect(lease.readOnly.value).toBe(false);

      lineage.value = null;
      await flushPromises();
      expect(release).toHaveBeenCalledWith(OTHER_LINEAGE, "tab-a");
      expect(lease.readOnly.value).toBe(true);
    } finally {
      scope.stop();
    }
  });
});
