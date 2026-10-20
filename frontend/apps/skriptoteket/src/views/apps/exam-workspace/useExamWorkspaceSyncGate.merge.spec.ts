/**
 * Exam workspace sync gate: the single merge point (TASK-SKRIPT-40-04-14,
 * G1b). One merge call per successful fresh load; the kept edit clears only
 * when a store in the merge generation reports back through `noteStored`.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  createGate,
  exam,
  LINEAGE,
  pointsOf,
  response,
  stepListRead,
  succeedLoad,
  withPoints,
  type SyncGateHarness,
} from "./useExamWorkspaceSyncGate.specSupport";

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

function mergedAt(harness: SyncGateHarness, index: number): NativeExamDocument {
  const document = harness.mergedInstalled[index];
  if (document === undefined) {
    throw new Error(`expected installed merge ${index}`);
  }
  return document;
}

describe("the sync gate merge point", () => {
  it("merges exactly once on a takeover load and queues one ordinary store", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    // The clean open installed once; only the merge installs after it.
    expect(harness.freshInstalled.length).toBe(1);
    expect(harness.mergedInstalled.length).toBe(1);
    expect(pointsOf(mergedAt(harness, 0), "item_001")).toBe(7);
    expect(harness.counts.storeRequests).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("holds the fresh document with a kept edit and installs only the merge", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    const documentRead = harness.documentReads[harness.documentReads.length - 1];
    if (documentRead === undefined) {
      throw new Error("expected a document read");
    }
    const fresh = exam();
    documentRead.resolve(response(fresh, "step-0"));
    await harness.settle();
    // The clean open installed once; the held fresh copy adds nothing.
    expect(harness.freshInstalled.length).toBe(1);
    expect(harness.mergeCalls.length).toBe(0);
    const stepRead = harness.stepReads[harness.stepReads.length - 1];
    if (stepRead === undefined) {
      throw new Error("expected a step-list read");
    }
    stepRead.read.resolve(stepListRead());
    await harness.settle();
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.mergedInstalled.length).toBe(1);
  });

  it("merges exactly once when a reclaim restarts an in-flight load", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    harness.gate.leaseAcquired();
    const abandonedDocument = harness.documentReads[harness.documentReads.length - 2];
    if (abandonedDocument === undefined) {
      throw new Error("expected the abandoned document read");
    }
    abandonedDocument.resolve(response(exam(), "step-0"));
    await harness.settle();
    // The abandoned load stops before its step-list read.
    expect(harness.stepReads.length).toBe(1);
    expect(harness.mergeCalls.length).toBe(0);
    // Only the clean open installed; the abandoned load adds nothing.
    expect(harness.freshInstalled.length).toBe(1);
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("merges exactly once per load when a 409 lands during the merged store", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    harness.gate.staleConflict();
    expect(harness.gate.phase.value).toBe("loading");
    harness.gate.noteStored();
    await harness.settle();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("keeps the kept edit until a store in the merge generation reports back", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    harness.gate.staleConflict();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    harness.gate.noteStored();
    await harness.settle();
    harness.gate.staleConflict();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("clears the kept edit when the merged store reports back", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.counts.storeRequests).toBe(1);
    harness.gate.noteStored();
    await harness.settle();
    harness.gate.staleConflict();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("keeps the kept edit across a network failure: the history's retry stores it", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.counts.storeRequests).toBe(1);
    expect(harness.pendingTimers()).toBe(0);
    expect(harness.gate.phase.value).toBe("editing");
    // No store reported back yet, so the next conflict still merges again.
    harness.gate.staleConflict();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
  });

  it("captures the original edit plus later typing on a second refusal", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    const merged = mergedAt(harness, 0);
    harness.flags.pendingEdit = true;
    harness.flags.stepDocument = merged;
    harness.flags.workingCopy = withPoints(merged, 8);
    harness.gate.leaseLost();
    expect(harness.gate.phase.value).toBe("readonly");
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    const second = harness.mergeCalls[1];
    if (second === undefined) {
      throw new Error("expected the second merge");
    }
    expect(second.base).toBe(merged);
    expect(pointsOf(second.edited, "item_001")).toBe(8);
  });

  it("runs no merged store when the merge leaves no question", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.flags.mergeResult = null;
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.mergedInstalled.length).toBe(0);
    expect(harness.counts.storeRequests).toBe(0);
    expect(harness.gate.phase.value).toBe("editing");
  });
});
