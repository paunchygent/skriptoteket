/**
 * Exam workspace edit lease, renewal: the holder renews while the lease lives.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit K8, M2):
 *   The holder renews every 5 s. A renew refused with `EDIT_LEASE_HELD`
 *   turns read-only without a reload. Renewals that keep failing keep the
 *   hold only while the last success is within the 15 s lease TTL; once the
 *   TTL passes the tab turns read-only, retries the claim and reads the
 *   newest state when it takes the lease back. One failed renew followed by
 *   a success stays editable.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
import {
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

describe("useExamWorkspaceEditLease renewal", () => {
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

  it("turns read-only once the lease TTL passes while renews keep failing, then recovers", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      const renewSpy = vi
        .spyOn(fake.server, "renew")
        .mockRejectedValue(new ApiError({ code: "INTERNAL", message: "boom", status: 500 }));
      try {
        await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
        expect(first.lease.readOnly.value).toBe(false);
        await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
        expect(first.lease.readOnly.value).toBe(false);
        await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
        expect(first.lease.readOnly.value).toBe(true);
        expect(first.acquired).toEqual([]);

        // Renew and claim succeed again: the next retry takes the lease back.
        renewSpy.mockRestore();
        await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
        expect(first.lease.readOnly.value).toBe(false);
        expect(first.acquired).toEqual(["reloaded"]);
      } finally {
        renewSpy.mockRestore();
      }
    } finally {
      first.stop();
    }
  });

  it("stays editable when a single failed renew is followed by a success", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      const originalRenew = fake.server.renew.bind(fake.server);
      let failNext = true;
      const renewSpy = vi
        .spyOn(fake.server, "renew")
        .mockImplementation(async (lineage: string, tabId: string) => {
          if (failNext) {
            failNext = false;
            throw new ApiError({ code: "INTERNAL", message: "boom", status: 500 });
          }
          return originalRenew(lineage, tabId);
        });
      try {
        await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
        expect(first.lease.readOnly.value).toBe(false);
        await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
        expect(first.lease.readOnly.value).toBe(false);
        expect(first.acquired).toEqual([]);
      } finally {
        renewSpy.mockRestore();
      }
    } finally {
      first.stop();
    }
  });

  it("ignores a delayed renew success that arrives after a later lost result", async () => {
    const held: ExamWorkspaceEditLeaseResponse = {
      holder_tab_id: "tab-a",
      renewed_at: new Date(1_000_000).toISOString(),
      takeover_requested: false,
      takeover_requested_by: null,
    };
    const failed = new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
    let renewCalls = 0;
    let refuseClaims = false;
    let resolveDelayed: ((response: ExamWorkspaceEditLeaseResponse) => void) | null = null;
    const takeDelayed = (): ((response: ExamWorkspaceEditLeaseResponse) => void) | null => {
      const current = resolveDelayed;
      resolveDelayed = null;
      return current;
    };
    const server: ExamWorkspaceEditLeaseServer = {
      claim: () => (refuseClaims ? Promise.reject(failed) : Promise.resolve(held)),
      release: () => Promise.resolve(held),
      renew: () => {
        renewCalls += 1;
        // The first renew is delayed past the lease lifetime; the second
        // reports the lease lost before the delayed success arrives.
        if (renewCalls === 1) {
          return new Promise<ExamWorkspaceEditLeaseResponse>((resolve) => {
            resolveDelayed = resolve;
          });
        }
        return Promise.reject(failed);
      },
      requestTakeover: () => Promise.resolve(held),
    };
    const scope = effectScope();
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        isGuest: () => false,
        lineageId: () => LINEAGE,
        onAcquired: () => Promise.resolve(),
        onTakeoverRequested: () => Promise.resolve(),
        server,
        tabId: "tab-a",
      }),
    )!;
    try {
      await flushPromises();
      expect(lease.readOnly.value).toBe(false);
      // The first renew stays pending; the second reports the lease lost.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(lease.readOnly.value).toBe(true);
      // The delayed first success arrives after the loss: it must not revive
      // the lease, and it must not move the deadline to its receipt time.
      // Later claims stay refused, so no fresh claim can mask the revival.
      refuseClaims = true;
      const wake = takeDelayed();
      if (wake !== null) {
        wake(held);
      }
      await flushPromises();
      expect(lease.readOnly.value).toBe(true);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(lease.readOnly.value).toBe(true);
    } finally {
      scope.stop();
    }
  });

  it("turns read-only once the TTL passes while a renew never resolves", async () => {
    const held: ExamWorkspaceEditLeaseResponse = {
      holder_tab_id: "tab-a",
      renewed_at: new Date(1_000_000).toISOString(),
      takeover_requested: false,
      takeover_requested_by: null,
    };
    const server: ExamWorkspaceEditLeaseServer = {
      claim: () => Promise.resolve(held),
      release: () => Promise.resolve(held),
      // The transport hangs: no renew result ever arrives.
      renew: () => new Promise<ExamWorkspaceEditLeaseResponse>(() => {}),
      requestTakeover: () => Promise.resolve(held),
    };
    const scope = effectScope();
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        isGuest: () => false,
        lineageId: () => LINEAGE,
        onAcquired: () => Promise.resolve(),
        onTakeoverRequested: () => Promise.resolve(),
        server,
        tabId: "tab-a",
      }),
    )!;
    try {
      await flushPromises();
      expect(lease.readOnly.value).toBe(false);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(lease.readOnly.value).toBe(false);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(lease.readOnly.value).toBe(false);
      // 15 s since the last confirmed success with no result: the local
      // deadline is enforced even though every renew is still pending.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(lease.readOnly.value).toBe(true);
    } finally {
      scope.stop();
    }
  });
});
