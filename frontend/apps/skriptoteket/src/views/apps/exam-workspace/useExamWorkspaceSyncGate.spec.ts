/**
 * Exam workspace sync gate: phases, events, lease outcomes and the write
 * queue (TASK-SKRIPT-40-04-14, G1b). Pure state machine over transport
 * doubles; editing binds the ports to the existing owners.
 */

import { describe, expect, it, vi } from "vitest";

import {
  createGate,
  deferred,
  exam,
  LINEAGE,
  response,
  stepListRead,
  succeedLoad,
  withPoints,
  type SyncGateHarness,
} from "./useExamWorkspaceSyncGate.specSupport";

const OTHER_LINEAGE = "00000000-0000-4000-8000-000000000002";

async function openEditing(harness: SyncGateHarness): Promise<void> {
  harness.gate.openExam(LINEAGE, false);
  await succeedLoad(harness, exam());
}

async function takeKept(harness: SyncGateHarness): Promise<void> {
  await openEditing(harness);
  harness.flags.pendingEdit = true;
  harness.flags.stepDocument = exam();
  harness.flags.workingCopy = withPoints(exam(), 7);
  harness.gate.leaseLost();
  await harness.settle();
}

describe("the sync gate phases and events", () => {
  it("starts loading with every input locked and writes refused", async () => {
    const harness = createGate();
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.gate.editingLocked.value).toBe(true);
    expect(harness.gate.leaseReadOnly.value).toBe(false);
    const run = vi.fn(async () => "ran");
    await expect(harness.gate.enqueueWrite(run, "refused")).resolves.toBe("refused");
    expect(run).not.toHaveBeenCalled();
  });

  it("reaches editing after an open when the lease is held", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    expect(harness.gate.phase.value).toBe("loading");
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
    expect(harness.gate.editingLocked.value).toBe(false);
    expect(harness.gate.leaseReadOnly.value).toBe(false);
    const run = vi.fn(async () => "ran");
    await expect(harness.gate.enqueueWrite(run, "refused")).resolves.toBe("ran");
  });

  it("reaches readonly after an open when the lease is not held", async () => {
    const harness = createGate();
    harness.flags.leaseHeld = false;
    harness.gate.openExam(LINEAGE, false);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("readonly");
    expect(harness.gate.editingLocked.value).toBe(true);
    expect(harness.gate.leaseReadOnly.value).toBe(true);
  });

  it("reads only the step list when the opened response already installed the document", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, true);
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.documentReads.length).toBe(0);
    expect(harness.stepReads.length).toBe(1);
    await succeedLoad(harness, exam());
    expect(harness.appliedSteps[0]?.base).toBe(null);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("restarts the load when another exam opens", async () => {
    const harness = createGate();
    await openEditing(harness);
    const reads = harness.documentReads.length;
    harness.gate.openExam(OTHER_LINEAGE, false);
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.documentReads.length).toBe(reads + 1);
  });

  it("clears the kept edit on a lineage change", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.openExam(OTHER_LINEAGE, false);
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(0);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("ignores an abandoned read's late answer", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    const abandoned = harness.documentReads[0];
    if (abandoned === undefined) {
      throw new Error("expected the first document read");
    }
    harness.gate.openExam(OTHER_LINEAGE, false);
    abandoned.resolve(response(withPoints(exam(), 9), "step-0"));
    await harness.settle();
    expect(harness.freshInstalled.length).toBe(0);
    expect(harness.mergeCalls.length).toBe(0);
    expect(harness.gate.phase.value).toBe("loading");
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
    expect(harness.freshInstalled.length).toBe(1);
  });

  it("starts a fresh load on a lease acquired from readonly", async () => {
    const harness = createGate();
    harness.flags.leaseHeld = false;
    harness.gate.openExam(LINEAGE, false);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("readonly");
    harness.flags.leaseHeld = true;
    harness.gate.leaseAcquired();
    expect(harness.gate.phase.value).toBe("loading");
    const reads = harness.documentReads.length;
    expect(reads).toBe(2);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("ignores a lease acquired while loading: the load in flight reads the lease when it finishes", async () => {
    const harness = createGate();
    harness.flags.leaseHeld = false;
    harness.gate.openExam(LINEAGE, false);
    const first = harness.documentReads[0];
    if (first === undefined) {
      throw new Error("expected the first document read");
    }
    harness.flags.leaseHeld = true;
    harness.gate.leaseAcquired();
    expect(harness.documentReads.length).toBe(1);
    expect(harness.gate.phase.value).toBe("loading");
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
    expect(harness.freshInstalled.length).toBe(1);
  });

  it("ignores a lease acquired while editing", async () => {
    const harness = createGate();
    await openEditing(harness);
    const reads = harness.documentReads.length;
    harness.gate.leaseAcquired();
    expect(harness.documentReads.length).toBe(reads);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("reaches editing when an open claim without a live foreign lease arrives as lease acquired", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    harness.flags.leaseHeld = true;
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("stays readonly when failed retry claims never report lease acquired", async () => {
    const harness = createGate();
    harness.flags.leaseHeld = false;
    harness.gate.openExam(LINEAGE, false);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("readonly");
    const run = vi.fn(async () => "ran");
    await expect(harness.gate.enqueueWrite(run, "refused")).resolves.toBe("refused");
    expect(run).not.toHaveBeenCalled();
    expect(harness.gate.phase.value).toBe("readonly");
  });

  it("goes readonly when failed renewals arrive as lease lost", async () => {
    const harness = createGate();
    await openEditing(harness);
    harness.flags.pendingEdit = true;
    harness.flags.stepDocument = exam();
    harness.flags.workingCopy = withPoints(exam(), 7);
    harness.gate.leaseLost();
    expect(harness.gate.phase.value).toBe("readonly");
    expect(harness.gate.leaseReadOnly.value).toBe(true);
    expect(harness.counts.owedDropped).toBe(1);
  });

  it("goes readonly without a capture when the lease is lost with no pending edit", async () => {
    const harness = createGate();
    await openEditing(harness);
    harness.flags.pendingEdit = false;
    harness.gate.leaseLost();
    expect(harness.gate.phase.value).toBe("readonly");
    expect(harness.counts.owedDropped).toBe(1);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(0);
  });

  it("ignores a lease loss outside editing", async () => {
    const harness = createGate();
    harness.flags.leaseHeld = false;
    harness.gate.openExam(LINEAGE, false);
    await succeedLoad(harness, exam());
    const reads = harness.documentReads.length;
    harness.gate.leaseLost();
    expect(harness.gate.phase.value).toBe("readonly");
    expect(harness.documentReads.length).toBe(reads);
    expect(harness.counts.owedDropped).toBe(0);
  });

  it("retires the running load and goes readonly when the lease is lost during loading", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    harness.gate.leaseLost();
    expect(harness.gate.phase.value).toBe("readonly");
    expect(harness.counts.owedDropped).toBe(0);
    const abandoned = harness.documentReads[0];
    if (abandoned === undefined) {
      throw new Error("expected the first document read");
    }
    abandoned.resolve(response(exam(), "step-0"));
    await harness.settle();
    expect(harness.freshInstalled.length).toBe(0);
    expect(harness.gate.phase.value).toBe("readonly");
    harness.flags.leaseHeld = true;
    harness.gate.leaseAcquired();
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.documentReads.length).toBe(2);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("keeps a held kept edit when the lease is lost again during the takeover load", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    harness.gate.leaseLost();
    expect(harness.gate.phase.value).toBe("readonly");
    expect(harness.counts.owedDropped).toBe(1);
    expect(harness.mergeCalls.length).toBe(0);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("returns to loading for a fresh load on a stale-cursor 409", async () => {
    const harness = createGate();
    await openEditing(harness);
    harness.gate.staleConflict();
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.documentReads.length).toBe(2);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("reloads both reads when a foreign cursor arrives with a stale document", async () => {
    const harness = createGate();
    await openEditing(harness);
    harness.gate.foreignCursor(false);
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.documentReads.length).toBe(2);
    const documentRead = harness.documentReads[harness.documentReads.length - 1];
    if (documentRead === undefined) {
      throw new Error("expected a document read");
    }
    documentRead.resolve(response(exam(), "step-0"));
    await harness.settle();
    expect(harness.stepReads.length).toBe(2);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("reads only the step list when a foreign cursor arrives with this tab's fresh document", async () => {
    const harness = createGate();
    await openEditing(harness);
    harness.gate.foreignCursor(true);
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.documentReads.length).toBe(1);
    expect(harness.stepReads.length).toBe(2);
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("resolves every write kind as refused in loading without running it", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    const kinds = ["typing store", "owed snapshot", "ctrl+s", "undo move", "departure flush"];
    for (const kind of kinds) {
      const run = vi.fn(async () => `${kind} ran`);
      await expect(harness.gate.enqueueWrite(run, `${kind} refused`)).resolves.toBe(`${kind} refused`);
      expect(run).not.toHaveBeenCalled();
    }
    expect(harness.gate.phase.value).toBe("loading");
  });

  it("resolves every write kind as refused in readonly without running it", async () => {
    const harness = createGate();
    harness.flags.leaseHeld = false;
    harness.gate.openExam(LINEAGE, false);
    await succeedLoad(harness, exam());
    const kinds = ["typing store", "owed snapshot", "ctrl+s", "undo move", "departure flush"];
    for (const kind of kinds) {
      const run = vi.fn(async () => `${kind} ran`);
      await expect(harness.gate.enqueueWrite(run, `${kind} refused`)).resolves.toBe(`${kind} refused`);
      expect(run).not.toHaveBeenCalled();
    }
    expect(harness.gate.phase.value).toBe("readonly");
  });

  it("never runs a queued entry from an older generation", async () => {
    const harness = createGate();
    await openEditing(harness);
    const firstDone = deferred<string>();
    const firstRun = vi.fn(() => firstDone.promise);
    const secondRun = vi.fn(async () => "second ran");
    const first = harness.gate.enqueueWrite(firstRun, "first refused");
    const second = harness.gate.enqueueWrite(secondRun, "second refused");
    await harness.settle();
    expect(firstRun).toHaveBeenCalledTimes(1);
    harness.flags.pendingEdit = false;
    harness.gate.leaseLost();
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.gate.phase.value).toBe("editing");
    firstDone.resolve("first ran");
    await expect(first).resolves.toBe("first ran");
    await expect(second).resolves.toBe("second refused");
    expect(secondRun).not.toHaveBeenCalled();
  });

  it("keeps loading and the kept edit when the document read fails, then retries", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    const read = harness.documentReads[harness.documentReads.length - 1];
    if (read === undefined) {
      throw new Error("expected a document read");
    }
    read.reject(new Error("network down"));
    await harness.settle();
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.stepResets()).toBe(0);
    expect(harness.counts.reloadFailures).toBe(1);
    expect(harness.pendingTimers()).toBe(1);
    harness.fireTimer();
    expect(harness.documentReads.length).toBe(3);
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("keeps loading and the kept edit when the step-list read fails, then retries", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    const documentRead = harness.documentReads[harness.documentReads.length - 1];
    if (documentRead === undefined) {
      throw new Error("expected a document read");
    }
    documentRead.resolve(response(exam(), "step-0"));
    await harness.settle();
    // The clean open installed once; the held fresh copy adds nothing.
    expect(harness.freshInstalled.length).toBe(1);
    const stepRead = harness.stepReads[harness.stepReads.length - 1];
    if (stepRead === undefined) {
      throw new Error("expected a step-list read");
    }
    stepRead.read.reject(new Error("network down"));
    await harness.settle();
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.stepResets()).toBe(1);
    expect(harness.counts.reloadFailures).toBe(1);
    harness.fireTimer();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("installs a clean document at once but edits only after the steps arrive", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    const documentRead = harness.documentReads[0];
    if (documentRead === undefined) {
      throw new Error("expected a document read");
    }
    documentRead.resolve(response(exam(), "step-0"));
    await harness.settle();
    expect(harness.freshInstalled.length).toBe(1);
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.gate.editingLocked.value).toBe(true);
    const stepRead = harness.stepReads[0];
    if (stepRead === undefined) {
      throw new Error("expected a step-list read");
    }
    stepRead.read.resolve(stepListRead());
    await harness.settle();
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("abandons the in-flight load and refuses writes on dispose", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    harness.gate.dispose();
    const documentRead = harness.documentReads[0];
    if (documentRead === undefined) {
      throw new Error("expected a document read");
    }
    documentRead.resolve(response(exam(), "step-0"));
    await harness.settle();
    expect(harness.freshInstalled.length).toBe(0);
    expect(harness.counts.reloadFailures).toBe(0);
    expect(harness.pendingTimers()).toBe(0);
    const run = vi.fn(async () => "ran");
    await expect(harness.gate.enqueueWrite(run, "refused")).resolves.toBe("refused");
    expect(run).not.toHaveBeenCalled();
  });
});
