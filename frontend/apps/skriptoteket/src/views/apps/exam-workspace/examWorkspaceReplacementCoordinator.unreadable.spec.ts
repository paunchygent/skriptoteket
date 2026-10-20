/**
 * Exam workspace coordinator: an unreadable route target recovers like a
 * failure but reports through its own port (TASK-SKRIPT-41-02-06, U5).
 *
 * Expected behavior:
 *   A route open that fails while current because the stored file cannot be
 *   read ("unreadable") takes the same recovery as "failed": the retained
 *   source is projected and recovered. It then calls the new
 *   `notifyRouteUnreadable` port with the intent lineage instead of
 *   `notifyRouteFailed`, and resolves the entry with "unreadable". An
 *   ordinary failure keeps calling `notifyRouteFailed` and resolves "failed".
 */

import { describe, expect, it } from "vitest";

import { createReplacementCoordinator } from "./examWorkspaceReplacementCoordinator";
import type {
  ExamWorkspaceReplacementDeps,
  ExamWorkspaceRouteOpenOutcome,
} from "./examWorkspaceReplacementTypes";
import { createSyncFence } from "./examWorkspaceSyncFence";

const RETAINED = "11111111-0000-4000-8000-000000000001";
const TARGET = "22222222-0000-4000-8000-000000000002";

function createHarness(openOutcome: ExamWorkspaceRouteOpenOutcome) {
  const fence = createSyncFence();
  const calls: {
    notifiedFailed: number;
    notifiedUnreadable: string[];
    projected: Array<string | null>;
    recovered: number;
  } = {
    notifiedFailed: 0,
    notifiedUnreadable: [],
    projected: [],
    recovered: 0,
  };
  const deps: ExamWorkspaceReplacementDeps = {
    abandonAttempt: () => undefined,
    adoptSelectedOpening: () => undefined,
    beginCopy: () => null,
    captureKept: () => undefined,
    claimSelectedLease: () => undefined,
    fence,
    hasActiveStore: () => false,
    hasUnconfirmed: () => false,
    installReplacementDocument: () => undefined,
    installedSource: () => RETAINED,
    isDisposed: () => false,
    isEditing: () => false,
    isVisibleDirty: () => false,
    notifyCopyFailed: () => undefined,
    notifyRouteFailed: () => {
      calls.notifiedFailed += 1;
    },
    notifyRouteUnreadable: (lineageId) => {
      calls.notifiedUnreadable.push(lineageId);
    },
    openRouteTarget: () => Promise.resolve(openOutcome),
    projectAddress: (lineageId) => {
      calls.projected.push(lineageId);
    },
    recoverRetainedSource: () => {
      calls.recovered += 1;
    },
    releaseCopyBusy: () => undefined,
    replaceCopy: (run) => run(),
    retireGeneration: () => undefined,
    settleEdit: () => Promise.resolve(true),
    waitForRouterIdle: () => Promise.resolve(),
  };
  return { calls, coordinator: createReplacementCoordinator(deps) };
}

describe("examWorkspaceReplacementCoordinator unreadable route", () => {
  it("recovers the retained source and reports the lineage through notifyRouteUnreadable", async () => {
    const { calls, coordinator } = createHarness("unreadable");

    const outcome = await coordinator.submitRoute(TARGET);

    expect(outcome).toBe("unreadable");
    expect(calls.notifiedUnreadable).toEqual([TARGET]);
    expect(calls.notifiedFailed).toBe(0);
    expect(calls.recovered).toBe(1);
    expect(calls.projected).toEqual([TARGET, RETAINED]);
  });

  it("an ordinary failure keeps reporting through notifyRouteFailed", async () => {
    const { calls, coordinator } = createHarness("failed");

    const outcome = await coordinator.submitRoute(TARGET);

    expect(outcome).toBe("failed");
    expect(calls.notifiedFailed).toBe(1);
    expect(calls.notifiedUnreadable).toEqual([]);
    expect(calls.recovered).toBe(1);
    expect(calls.projected).toEqual([TARGET, RETAINED]);
  });
});
