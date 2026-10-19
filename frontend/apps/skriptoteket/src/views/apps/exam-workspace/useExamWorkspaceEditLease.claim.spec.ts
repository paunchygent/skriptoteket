/**
 * Exam workspace edit lease, open claim: one editing tab on the server lease.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit K8):
 *   One random tab id per page load; claim on opening an exam. A second tab
 *   opens read-only when the claim meets a live foreign lease. Any other
 *   claim failure stays editable on open, since the write guard is
 *   authoritative. A read-only tab retries its refused claim at the heartbeat
 *   cadence and takes the lease as soon as it is free (expired or released)
 *   with no `Ta över`; a retry claim that fails stays read-only.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import {
  createExamWorkspaceEditLeaseTabId,
  EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS,
  EXAM_WORKSPACE_EDIT_LEASE_TTL_MS,
  useExamWorkspaceEditLease,
  type ExamWorkspaceEditLeaseServer,
} from "./useExamWorkspaceEditLease";
import {
  createFakeLeaseServer,
  LINEAGE,
  setupLease,
} from "./useExamWorkspaceEditLease.specSupport";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useExamWorkspaceEditLease open claim", () => {
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

  it("stays editable when the open claim fails with a 500 or a network error", async () => {
    const failures: Error[] = [
      new ApiError({ code: "INTERNAL", message: "boom", status: 500 }),
      new TypeError("offline"),
    ];
    for (const failure of failures) {
      const failing: ExamWorkspaceEditLeaseServer = {
        claim: () => Promise.reject(failure),
        release: () => Promise.reject(failure),
        renew: () => Promise.reject(failure),
        requestTakeover: () => Promise.reject(failure),
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
      } finally {
        scope.stop();
      }
    }
  });

  it("stays read-only when a retry claim fails with a 500 or a network error, then takes the freed lease", async () => {
    const fake = createFakeLeaseServer();
    const holder = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      expect(holder.lease.readOnly.value).toBe(false);
      const waiter = setupLease(fake, { tabId: "tab-a" });
      try {
        await flushPromises();
        expect(waiter.lease.readOnly.value).toBe(true);
        const originalClaim = fake.server.claim.bind(fake.server);
        let failure: unknown = new ApiError({ code: "INTERNAL", message: "boom", status: 500 });
        const claimSpy = vi
          .spyOn(fake.server, "claim")
          .mockImplementation(async (lineage: string, tabId: string) => {
            if (tabId === "tab-a" && failure !== null) {
              throw failure;
            }
            return originalClaim(lineage, tabId);
          });
        try {
          await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
          expect(waiter.lease.readOnly.value).toBe(true);
          expect(waiter.acquired).toEqual([]);
          failure = new TypeError("offline");
          await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
          expect(waiter.lease.readOnly.value).toBe(true);
          expect(waiter.acquired).toEqual([]);

          // The holder releases; the next retry claims the freed lease.
          failure = null;
          await fake.server.release(LINEAGE, "tab-b");
          await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
          expect(fake.state().holder).toBe("tab-a");
          expect(waiter.lease.readOnly.value).toBe(false);
          expect(waiter.acquired).toEqual(["reloaded"]);
        } finally {
          claimSpy.mockRestore();
        }
      } finally {
        waiter.stop();
      }
    } finally {
      holder.stop();
    }
  });

  it("claims the freed lease on the next heartbeat after a refused write", async () => {
    const fake = createFakeLeaseServer();
    const claim = vi.spyOn(fake.server, "claim");
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      // Another tab owns the lease now; the write guard reports the loss.
      fake.advance(EXAM_WORKSPACE_EDIT_LEASE_TTL_MS + 1);
      await fake.server.claim(LINEAGE, "tab-b");
      first.lease.noteLostLease();
      expect(first.lease.readOnly.value).toBe(true);
      const claimsAfterLoss = claim.mock.calls.length;

      await fake.server.release(LINEAGE, "tab-b");
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(claim.mock.calls.length).toBeGreaterThan(claimsAfterLoss);
      expect(first.lease.readOnly.value).toBe(false);
      expect(first.acquired).toEqual(["reloaded"]);
    } finally {
      first.stop();
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
});
