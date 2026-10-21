/**
 * Exam workspace coordinator: Nytt prov (TASK-SKRIPT-40-04-21, F1 repair).
 *
 * Expected behavior:
 *   Nytt prov is a third replacement intent, modelled on Spara som. With no
 *   source it selects at once and installs the begin response without
 *   settling; with a source the settle runs first and the begin runs only
 *   after it. A newer route during the settle supersedes it and the begin
 *   never runs. A refused begin (null) and a failed posting resolve
 *   "failed", notify once through `notifyNewExamFailed`, and leave the
 *   source behind: the copy busy is released, an edit is still accepted and
 *   stored, and a later route still installs. A newExam never starts behind
 *   a running replacement, and over an open source outside editing it ends
 *   without publishing.
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ExamWorkspaceDocumentResponse } from "../../../api/examWorkspace";
import { createReplacementCoordinator } from "./examWorkspaceReplacementCoordinator";
import type {
  ExamWorkspaceReplacementDeps,
  ExamWorkspaceRouteOpenOutcome,
} from "./examWorkspaceReplacementTypes";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { buildResponse } from "./useExamWorkspaceDocument.specSupport";

const SOURCE = "11111111-0000-4000-8000-000000000001";
const CURSOR = "22222222-0000-4000-8000-000000000002";
const TARGET = "33333333-0000-4000-8000-000000000003";

/** A manually completed promise, so the spec orders settle, begin and install. */
function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((run, fail) => {
    resolve = run;
    reject = fail;
  });
  return { promise, reject, resolve };
}

type Harness = {
  coordinator: ReturnType<typeof createReplacementCoordinator>;
  flags: {
    editing: boolean;
    source: string | null;
    settleImpl: () => Promise<boolean>;
    beginImpl: (expectedCursor: string | null) => Promise<ExamWorkspaceDocumentResponse> | null;
    routeImpl: (lineageId: string) => Promise<ExamWorkspaceRouteOpenOutcome>;
  };
  calls: {
    settled: number;
    kept: number;
    begins: Array<string | null>;
    installed: ExamWorkspaceDocumentResponse[];
    adopted: string[];
    projected: Array<string | null>;
    notifiedNewExamFailed: number;
    releasedCopyBusy: number;
    recovered: number;
  };
  copyBusyHeld: { value: boolean };
  /** The editor's admission lamp: true while editing and no copy holds the document. */
  attemptEdit: (label: string) => boolean;
  storedEdits: string[];
};

function createHarness(): Harness {
  const fence = createSyncFence();
  const copyBusyHeld = { value: false };
  const storedEdits: string[] = [];
  const flags: Harness["flags"] = {
    beginImpl: () => Promise.resolve(buildResponse()),
    editing: true,
    routeImpl: () => Promise.resolve("installed"),
    settleImpl: () => Promise.resolve(true),
    source: SOURCE,
  };
  const calls: Harness["calls"] = {
    adopted: [],
    begins: [],
    installed: [],
    kept: 0,
    notifiedNewExamFailed: 0,
    projected: [],
    recovered: 0,
    releasedCopyBusy: 0,
    settled: 0,
  };
  const deps: ExamWorkspaceReplacementDeps = {
    abandonAttempt: () => undefined,
    adoptSelectedOpening: (lineageId) => {
      calls.adopted.push(lineageId);
    },
    beginCopy: () => null,
    beginNewExam: (expectedCursor) => {
      calls.begins.push(expectedCursor);
      const posting = flags.beginImpl(expectedCursor);
      if (posting === null) {
        return null;
      }
      // The production hold: the busy belongs to this creation's own fence
      // token, so a retired creation's late settle never clears a newer one.
      copyBusyHeld.value = true;
      const token = fence.begin();
      return posting.then(
        (response) => {
          if (fence.isCurrent(token)) {
            copyBusyHeld.value = false;
          }
          return response;
        },
        (error: unknown) => {
          if (fence.isCurrent(token)) {
            copyBusyHeld.value = false;
          }
          throw error;
        },
      );
    },
    captureKept: () => {
      calls.kept += 1;
    },
    claimSelectedLease: () => undefined,
    fence,
    hasActiveStore: () => false,
    hasUnconfirmed: () => false,
    installedSource: () => flags.source,
    installReplacementDocument: (token, response) => {
      void token;
      calls.installed.push(response);
    },
    isDisposed: () => false,
    isEditing: () => flags.editing,
    isVisibleDirty: () => false,
    notifyCopyFailed: () => undefined,
    notifyNewExamFailed: () => {
      calls.notifiedNewExamFailed += 1;
    },
    notifyRouteFailed: () => undefined,
    notifyRouteUnreadable: () => undefined,
    openRouteTarget: (lineageId) => flags.routeImpl(lineageId),
    projectAddress: (lineageId) => {
      calls.projected.push(lineageId);
    },
    recoverRetainedSource: () => {
      calls.recovered += 1;
    },
    releaseCopyBusy: () => {
      calls.releasedCopyBusy += 1;
      copyBusyHeld.value = false;
    },
    replaceCopy: (run) => run(),
    retireGeneration: () => fence.retire(),
    settleEdit: () => {
      calls.settled += 1;
      return flags.settleImpl();
    },
    waitForRouterIdle: () => Promise.resolve(),
  };
  return {
    attemptEdit: (label) => {
      if (!flags.editing || copyBusyHeld.value) {
        return false;
      }
      storedEdits.push(label);
      return true;
    },
    calls,
    coordinator: createReplacementCoordinator(deps),
    copyBusyHeld,
    flags,
    storedEdits,
  };
}

describe("examWorkspaceReplacementCoordinator newExam", () => {
  it("with no source selects at once and installs the begin response", async () => {
    const harness = createHarness();
    harness.flags.source = null;
    harness.flags.editing = false;

    const outcome = harness.coordinator.submitNewExam(null);
    expect(harness.calls.begins).toEqual([null]);
    expect(harness.calls.settled).toBe(0);

    await expect(outcome).resolves.toBe("created");
    await flushPromises();
    expect(harness.calls.installed).toHaveLength(1);
    expect(harness.calls.adopted).toEqual(["lineage-1"]);
    expect(harness.calls.projected).toEqual(["lineage-1"]);
    expect(harness.calls.notifiedNewExamFailed).toBe(0);
  });

  it("with a source the settle runs first and the begin runs only after it", async () => {
    const harness = createHarness();
    const settle = deferred<boolean>();
    const posting = deferred<ExamWorkspaceDocumentResponse>();
    harness.flags.settleImpl = () => settle.promise;
    harness.flags.beginImpl = () => posting.promise;

    const outcome = harness.coordinator.submitNewExam(CURSOR);
    await flushPromises();
    expect(harness.calls.settled).toBe(1);
    expect(harness.calls.begins).toEqual([]);

    settle.resolve(true);
    await flushPromises();
    expect(harness.calls.begins).toEqual([CURSOR]);

    posting.resolve(buildResponse());
    await expect(outcome).resolves.toBe("created");
    expect(harness.calls.adopted).toEqual(["lineage-1"]);
  });

  it("a duplicate submit while the same newExam entry is desired returns its promise", async () => {
    const harness = createHarness();
    const settle = deferred<boolean>();
    harness.flags.settleImpl = () => settle.promise;

    const first = harness.coordinator.submitNewExam(CURSOR);
    const duplicate = harness.coordinator.submitNewExam(CURSOR);
    expect(duplicate).toBe(first);
    const other = harness.coordinator.submitNewExam(null);
    expect(other).not.toBe(first);

    settle.resolve(true);
    await expect(first).resolves.toBe("failed");
    await expect(other).resolves.toBe("created");
    expect(harness.calls.begins).toEqual([null]);
  });

  it("a newer route during the settle supersedes it and the begin never runs", async () => {
    const harness = createHarness();
    const settle = deferred<boolean>();
    const route = deferred<ExamWorkspaceRouteOpenOutcome>();
    harness.flags.settleImpl = () => settle.promise;
    harness.flags.routeImpl = () => route.promise;

    const creating = harness.coordinator.submitNewExam(CURSOR);
    await flushPromises();
    const opening = harness.coordinator.submitRoute(TARGET);
    await expect(creating).resolves.toBe("failed");

    settle.resolve(true);
    await flushPromises();
    expect(harness.calls.begins).toEqual([]);

    route.resolve("installed");
    await expect(opening).resolves.toBe("installed");
    expect(harness.calls.notifiedNewExamFailed).toBe(0);
    expect(harness.attemptEdit("kept-typing")).toBe(true);
  });

  it("a refused begin keeps the source editable, notifies once and admits a later route", async () => {
    const harness = createHarness();
    harness.flags.beginImpl = () => null;

    await expect(harness.coordinator.submitNewExam(CURSOR)).resolves.toBe("failed");
    expect(harness.calls.begins).toEqual([CURSOR]);
    expect(harness.calls.notifiedNewExamFailed).toBe(1);
    expect(harness.copyBusyHeld.value).toBe(false);
    expect(harness.attemptEdit("after-refusal")).toBe(true);
    expect(harness.storedEdits).toEqual(["after-refusal"]);

    await expect(harness.coordinator.submitRoute(TARGET)).resolves.toBe("installed");
  });

  it("a failed posting keeps the source editable, notifies once and admits a later route", async () => {
    const harness = createHarness();
    const posting = deferred<ExamWorkspaceDocumentResponse>();
    harness.flags.beginImpl = () => posting.promise;
    expect(harness.attemptEdit("before-begin")).toBe(true);

    const outcome = harness.coordinator.submitNewExam(CURSOR);
    await flushPromises();
    expect(harness.attemptEdit("while-pending")).toBe(false);

    posting.reject(new Error("blank failed"));
    await expect(outcome).resolves.toBe("failed");
    await flushPromises();
    expect(harness.calls.notifiedNewExamFailed).toBe(1);
    expect(harness.copyBusyHeld.value).toBe(false);
    expect(harness.attemptEdit("after-failure")).toBe(true);
    expect(harness.storedEdits).toEqual(["before-begin", "after-failure"]);

    await expect(harness.coordinator.submitRoute(TARGET)).resolves.toBe("installed");
  });

  it("a newExam never starts behind a running replacement", async () => {
    const harness = createHarness();
    harness.flags.editing = false;
    harness.flags.source = SOURCE;
    const route = deferred<ExamWorkspaceRouteOpenOutcome>();
    harness.flags.routeImpl = () => route.promise;

    const opening = harness.coordinator.submitRoute(TARGET);
    await flushPromises();
    await expect(harness.coordinator.submitNewExam(CURSOR)).resolves.toBe("failed");
    expect(harness.calls.begins).toEqual([]);
    expect(harness.calls.projected).toEqual([TARGET]);

    route.resolve("installed");
    await flushPromises();
    await expect(opening).resolves.toBe("superseded");
    expect(harness.calls.installed).toEqual([]);
  });

  it("over an open source outside editing it ends without publishing", async () => {
    const harness = createHarness();
    harness.flags.editing = false;

    await expect(harness.coordinator.submitNewExam(CURSOR)).resolves.toBe("failed");
    expect(harness.calls.begins).toEqual([]);
    expect(harness.calls.projected).toEqual([]);
    expect(harness.calls.notifiedNewExamFailed).toBe(0);
  });
});
