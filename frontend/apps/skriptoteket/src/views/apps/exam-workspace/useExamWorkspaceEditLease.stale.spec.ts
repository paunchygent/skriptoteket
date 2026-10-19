/**
 * Exam workspace edit lease, stale claim answers: an obsolete visit must not
 * free the current lease.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4):
 *   An obsolete claim answer never releases a lease this tab currently holds,
 *   or is currently acquiring, for the current lineage. Stale-answer
 *   bookkeeping stays apart from the live owner identity (lineage plus tab).
 *   Only a lineage that is no longer current, or a disposed composable, is
 *   released. The duplicate-success no-op, the epoch and renew-sequence
 *   ordering, and first-claim-wins stay unchanged.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
import {
  useExamWorkspaceEditLease,
  type ExamWorkspaceEditLeaseServer,
} from "./useExamWorkspaceEditLease";

const EXAM_ONE = "stale-exam-one";
const EXAM_TWO = "stale-exam-two";

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
}

function leaseResponse(holder: string | null): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: new Date(1_000_000).toISOString(),
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function deferred<T>() {
  let resolve: (value: T) => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<T>((settle, fail) => {
    resolve = settle;
    reject = fail;
  });
  return { promise, reject, resolve };
}

type StaleServer = {
  driver: ExamWorkspaceEditLeaseServer;
  holders: Map<string, string>;
  releases: Array<{ lineage: string; tab: string }>;
  gate: ReturnType<typeof deferred<ExamWorkspaceEditLeaseResponse>>;
  armDelayedClaim: () => void;
};

function createStaleServer(): StaleServer {
  const holders = new Map<string, string>([[EXAM_ONE, "tab-b"]]);
  const releases: Array<{ lineage: string; tab: string }> = [];
  const gate = deferred<ExamWorkspaceEditLeaseResponse>();
  let delayNextAClaim = false;
  const driver: ExamWorkspaceEditLeaseServer = {
    claim: (lineage: string, tab: string) => {
      if (holders.has(lineage) && holders.get(lineage) !== tab) {
        return Promise.reject(heldError());
      }
      holders.set(lineage, tab);
      if (lineage === EXAM_ONE && tab === "tab-a" && delayNextAClaim) {
        delayNextAClaim = false;
        return gate.promise;
      }
      return Promise.resolve(leaseResponse(tab));
    },
    release: (lineage: string, tab: string) => {
      releases.push({ lineage, tab });
      if (holders.get(lineage) !== tab) {
        return Promise.reject(heldError());
      }
      holders.delete(lineage);
      return Promise.resolve(leaseResponse(null));
    },
    renew: (lineage: string, tab: string) => {
      if (holders.get(lineage) !== tab) {
        return Promise.reject(heldError());
      }
      return Promise.resolve(leaseResponse(tab));
    },
    requestTakeover: () => Promise.resolve(leaseResponse("tab-b")),
  };
  return {
    armDelayedClaim: () => {
      delayNextAClaim = true;
    },
    driver,
    gate,
    holders,
    releases,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useExamWorkspaceEditLease stale claim answers", () => {
  it("a late claim for an earlier visit to the same exam never releases the current visit lease", async () => {
    const stale = createStaleServer();
    const lineage = ref<string | null>(EXAM_ONE);
    const scope = effectScope();
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        isGuest: () => false,
        lineageId: () => lineage.value,
        onAcquired: () => Promise.resolve(),
        onTakeoverRequested: () => Promise.resolve(),
        server: stale.driver,
        tabId: "tab-a",
      }),
    );
    if (lease === undefined) {
      throw new Error("lease missing");
    }
    const current = lease;
    try {
      await flushPromises();
      expect(current.readOnly.value).toBe(true);

      stale.holders.delete(EXAM_ONE);
      stale.armDelayedClaim();
      await vi.advanceTimersByTimeAsync(5_000);
      expect(stale.holders.get(EXAM_ONE)).toBe("tab-a");

      lineage.value = EXAM_TWO;
      await flushPromises();
      lineage.value = EXAM_ONE;
      await flushPromises();
      expect(current.readOnly.value).toBe(false);

      stale.gate.resolve(leaseResponse("tab-a"));
      await flushPromises();

      const otherScope = effectScope();
      const other = otherScope.run(() =>
        useExamWorkspaceEditLease({
          isGuest: () => false,
          lineageId: () => EXAM_ONE,
          onAcquired: () => Promise.resolve(),
          onTakeoverRequested: () => Promise.resolve(),
          server: stale.driver,
          tabId: "tab-b",
        }),
      );
      if (other === undefined) {
        throw new Error("other lease missing");
      }
      try {
        await flushPromises();
        expect({
          editableA: current.readOnly.value === false,
          editableB: other.readOnly.value === false,
          holder: stale.holders.get(EXAM_ONE),
        }).toEqual({ editableA: true, editableB: false, holder: "tab-a" });
        expect(stale.releases.filter((entry) => entry.lineage === EXAM_ONE)).toEqual([]);
      } finally {
        otherScope.stop();
      }
    } finally {
      scope.stop();
    }
  });

  it("a late claim for an exam that is no longer open is still released", async () => {
    const stale = createStaleServer();
    const lineage = ref<string | null>(EXAM_ONE);
    const scope = effectScope();
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        isGuest: () => false,
        lineageId: () => lineage.value,
        onAcquired: () => Promise.resolve(),
        onTakeoverRequested: () => Promise.resolve(),
        server: stale.driver,
        tabId: "tab-a",
      }),
    );
    if (lease === undefined) {
      throw new Error("lease missing");
    }
    const current = lease;
    try {
      await flushPromises();
      expect(current.readOnly.value).toBe(true);

      stale.holders.delete(EXAM_ONE);
      stale.armDelayedClaim();
      await vi.advanceTimersByTimeAsync(5_000);
      expect(stale.holders.get(EXAM_ONE)).toBe("tab-a");

      lineage.value = EXAM_TWO;
      await flushPromises();
      expect(current.readOnly.value).toBe(false);

      stale.gate.resolve(leaseResponse("tab-a"));
      await flushPromises();

      expect(stale.holders.has(EXAM_ONE)).toBe(false);
      expect(stale.holders.get(EXAM_TWO)).toBe("tab-a");
      expect(stale.releases.filter((entry) => entry.lineage === EXAM_ONE).length).toBe(1);
      expect(stale.releases.filter((entry) => entry.lineage === EXAM_TWO)).toEqual([]);
      expect(current.readOnly.value).toBe(false);
    } finally {
      scope.stop();
    }
  });
});
