/**
 * Exam workspace edit lease, `Ta över`: wait for the holder to yield.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit K8):
 *   `Ta över` requests the lease and claims it once the holder has released
 *   or its lease has expired, then reads the newest state. The holder sees
 *   the request at its next renew, stores its pending edit, releases and
 *   turns read-only. While waiting the tab stays read-only; a poll claim
 *   that fails stays waiting. After yielding the tab restarts its heartbeat,
 *   so its first retry claim happens one full heartbeat after the release
 *   instead of racing the waiting tab's poll.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
import {
  EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS,
  EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS,
  useExamWorkspaceEditLease,
  type ExamWorkspaceEditLeaseServer,
} from "./useExamWorkspaceEditLease";
import { createSyncFence } from "./examWorkspaceSyncFence";
import {
  createFakeLeaseServer,
  LINEAGE,
  OTHER_LINEAGE,
  setupLease,
} from "./useExamWorkspaceEditLease.specSupport";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useExamWorkspaceEditLease takeover", () => {
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

  it("takes the lease back on the next heartbeat after yielding it", async () => {
    const fake = createFakeLeaseServer();
    const claim = vi.spyOn(fake.server, "claim");
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      const taking = second.lease.requestTakeover();
      await flushPromises();
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      await taking;
      expect(first.lease.readOnly.value).toBe(true);
      expect(first.flushed).toEqual(["stored"]);
      expect(fake.state().holder).toBe("tab-b");
      const claimsAfterYield = claim.mock.calls.length;
      expect(claimsAfterYield).toBeGreaterThan(0);

      // The taking tab closes: its dispose release frees the lease.
      second.stop();
      await flushPromises();
      expect(fake.state().holder).toBeNull();

      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(claim.mock.calls.length).toBeGreaterThan(claimsAfterYield);
      expect(fake.state().holder).toBe("tab-a");
      expect(first.lease.readOnly.value).toBe(false);
      expect(first.acquired).toEqual(["reloaded", "reloaded"]);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("stays read-only while the new holder keeps a live lease after a yield", async () => {
    const fake = createFakeLeaseServer();
    const claim = vi.spyOn(fake.server, "claim");
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      const taking = second.lease.requestTakeover();
      await flushPromises();
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      await taking;
      expect(first.lease.readOnly.value).toBe(true);
      expect(fake.state().holder).toBe("tab-b");
      const claimsAfterYield = claim.mock.calls.length;

      // The holder stays live: retries are refused, no flip-flop.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(claim.mock.calls.length).toBeGreaterThan(claimsAfterYield);
      expect(first.lease.readOnly.value).toBe(true);
      expect(first.acquired).toEqual(["reloaded"]);
      expect(fake.state().holder).toBe("tab-b");
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("keeps a Ta över wait read-only while poll claims fail with a non-409 error", async () => {
    const fake = createFakeLeaseServer();
    const holder = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      const waiter = setupLease(fake, { tabId: "tab-a" });
      try {
        await flushPromises();
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
          const taking = waiter.lease.requestTakeover();
          await flushPromises();
          await vi.advanceTimersByTimeAsync(3 * EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
          expect(waiter.lease.waiting.value).toBe(true);
          expect(waiter.lease.readOnly.value).toBe(true);
          expect(waiter.acquired).toEqual([]);
          failure = new TypeError("offline");
          await vi.advanceTimersByTimeAsync(2 * EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
          expect(waiter.lease.waiting.value).toBe(true);
          expect(waiter.lease.readOnly.value).toBe(true);
          expect(waiter.acquired).toEqual([]);

          // The holder releases; the next poll claims the freed lease. (The
          // holder may also have yielded on its own heartbeat after seeing
          // the request, so always advance to the next poll either way.)
          failure = null;
          if (fake.state().holder === "tab-b") {
            await fake.server.release(LINEAGE, "tab-b");
          }
          await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
          await taking;
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

  it("waits one full heartbeat after a yield before claiming again, letting the waiter take over", async () => {
    const fake = createFakeLeaseServer();
    const claimSpy = vi.spyOn(fake.server, "claim");
    let delayTakeoverFlush = true;
    const first = setupLease(fake, {
      onTakeoverRequested: () =>
        new Promise<void>((resolve) => {
          if (delayTakeoverFlush) {
            delayTakeoverFlush = false;
            setTimeout(resolve, EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS - 100);
          } else {
            resolve();
          }
        }),
      tabId: "tab-a",
    });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      expect(second.lease.readOnly.value).toBe(true);
      const taking = second.lease.requestTakeover();
      await flushPromises();
      expect(fake.state().waiting).toBe("tab-b");

      // The holder's next renew starts the slow yield; the release lands just
      // before its old heartbeat phase would fire again.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS - 100);
      expect(first.lease.readOnly.value).toBe(true);
      const claimsFromYielded = claimSpy.mock.calls.filter((call) => call[1] === "tab-a").length;

      // 200 ms later the old phase would already have fired: the yielded tab
      // must still have sent no claim, while the waiter's poll takes the lease.
      // (Assert before awaiting the takeover: on the old phase the yielded
      // tab reclaims first and the waiter never resolves here.)
      await vi.advanceTimersByTimeAsync(200);
      expect(claimSpy.mock.calls.filter((call) => call[1] === "tab-a").length).toBe(
        claimsFromYielded,
      );
      await taking;
      expect(fake.state().holder).toBe("tab-b");
      expect(second.lease.readOnly.value).toBe(false);
      expect(second.acquired).toEqual(["reloaded"]);
      expect(first.lease.readOnly.value).toBe(true);

      // One full heartbeat after the release the yielded tab retries once and
      // is refused, staying read-only without a reload.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_HEARTBEAT_MS);
      expect(claimSpy.mock.calls.filter((call) => call[1] === "tab-a").length).toBe(
        claimsFromYielded + 1,
      );
      expect(fake.state().holder).toBe("tab-b");
      expect(first.lease.readOnly.value).toBe(true);
      expect(first.acquired).toEqual(["reloaded"]);
    } finally {
      first.stop();
      second.stop();
      claimSpy.mockRestore();
    }
  });

  it("releases a late old-exam poll claim and keeps the new exam read-only", async () => {
    // Waiting on exam X with a poll claim in flight, the teacher opens exam
    // Y (refused: another tab holds it), then X's claim succeeds. Y must stay
    // read-only and X's lease must be released.
    const heldX: ExamWorkspaceEditLeaseResponse = {
      holder_tab_id: "tab-a",
      renewed_at: new Date(1_000_000).toISOString(),
      takeover_requested: false,
      takeover_requested_by: null,
    };
    const refused = new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
    let xClaims = 0;
    let resolveLateClaim: ((response: ExamWorkspaceEditLeaseResponse) => void) | null = null;
    const takeLateClaim = (): ((response: ExamWorkspaceEditLeaseResponse) => void) | null => {
      const current = resolveLateClaim;
      resolveLateClaim = null;
      return current;
    };
    const releases: string[] = [];
    const server: ExamWorkspaceEditLeaseServer = {
      claim: (lineage: string) => {
        if (lineage !== LINEAGE) {
          return Promise.reject(refused);
        }
        xClaims += 1;
        // Open claim plus the takeover request's immediate claim are refused;
        // the poll claim stays in flight until the test releases it.
        if (xClaims <= 2) {
          return Promise.reject(refused);
        }
        return new Promise<ExamWorkspaceEditLeaseResponse>((resolve) => {
          resolveLateClaim = resolve;
        });
      },
      release: (lineage: string) => {
        releases.push(lineage);
        return Promise.resolve(heldX);
      },
      renew: () => Promise.resolve(heldX),
      requestTakeover: () =>
        Promise.resolve({
          holder_tab_id: "tab-other",
          renewed_at: new Date(1_000_000).toISOString(),
          takeover_requested: false,
          takeover_requested_by: null,
        }),
    };
    const scope = effectScope();
    const lineage = ref<string | null>(LINEAGE);
    let acquired = 0;
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        fence: createSyncFence(),
        isGuest: () => false,
        lineageId: () => lineage.value,
        onLeaseAcquired: () => {
          acquired += 1;
        },
        onLeaseLost: () => undefined,
        onLeaseRefused: () => undefined,
        onPageHidden: () => undefined,
        onTakeoverRequested: () => Promise.resolve(),
        server,
        tabId: "tab-a",
      }),
    )!;
    lease.openLineage(LINEAGE);
    try {
      await flushPromises();
      expect(lease.readOnly.value).toBe(true);
      const taking = lease.requestTakeover();
      await flushPromises();
      expect(lease.waiting.value).toBe(true);
      // Let the poll sleep elapse so its claim is in flight.
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
      expect(resolveLateClaim).not.toBeNull();
      // The teacher opens exam Y, whose claim is refused.
      lineage.value = OTHER_LINEAGE;
      lease.openLineage(OTHER_LINEAGE);
      await flushPromises();
      expect(lease.readOnly.value).toBe(true);
      // X's old claim then succeeds: it must change nothing.
      const wake = takeLateClaim();
      if (wake !== null) {
        wake(heldX);
      }
      await flushPromises();
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
      expect(lease.readOnly.value).toBe(true);
      expect(acquired).toBe(0);
      expect(releases).toContain(LINEAGE);
      expect(lease.waiting.value).toBe(false);
      await taking;
    } finally {
      scope.stop();
    }
  });

  it("settles requestTakeover when disposed while the takeover poll sleeps", async () => {
    const fake = createFakeLeaseServer();
    const holder = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      const waiter = setupLease(fake, { tabId: "tab-a" });
      try {
        await flushPromises();
        let settled = false;
        const taking = waiter.lease.requestTakeover().then(() => {
          settled = true;
        });
        await flushPromises();
        expect(waiter.lease.waiting.value).toBe(true);
        // Dispose while the poll sleeps: the wait must settle, not hang.
        waiter.stop();
        await vi.advanceTimersByTimeAsync(3 * EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
        await flushPromises();
        expect(settled).toBe(true);
        await taking;
      } finally {
        waiter.stop();
      }
    } finally {
      holder.stop();
    }
  });

  it("settles requestTakeover when the lineage switches while the takeover poll sleeps", async () => {
    const fake = createFakeLeaseServer();
    const holder = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      const scope = effectScope();
      const lineage = ref<string | null>(LINEAGE);
      const lease = scope.run(() =>
        useExamWorkspaceEditLease({
          fence: createSyncFence(),
          isGuest: () => false,
          lineageId: () => lineage.value,
          onLeaseAcquired: () => undefined,
          onLeaseLost: () => undefined,
        onLeaseRefused: () => undefined,
        onPageHidden: () => undefined,
          onTakeoverRequested: () => Promise.resolve(),
          server: fake.server,
          tabId: "tab-a",
        }),
      )!;
      try {
        await flushPromises();
        expect(lease.readOnly.value).toBe(true);
        let settled = false;
        const taking = lease.requestTakeover().then(() => {
          settled = true;
        });
        await flushPromises();
        expect(lease.waiting.value).toBe(true);
        // Switch exams while the poll sleeps: the wait must settle, not hang.
        lineage.value = OTHER_LINEAGE;
        await flushPromises();
        await vi.advanceTimersByTimeAsync(3 * EXAM_WORKSPACE_EDIT_LEASE_TAKEOVER_POLL_MS);
        await flushPromises();
        expect(settled).toBe(true);
        await taking;
      } finally {
        scope.stop();
      }
    } finally {
      holder.stop();
    }
  });
});
