/**
 * Exam workspace sync gate: the single merge point (TASK-SKRIPT-40-04-14,
 * G1a). One merge call per successful fresh load; the kept edit clears only
 * after the merged store reports stored.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  createGate,
  deferred,
  exam,
  LINEAGE,
  pointsOf,
  succeedLoad,
  withPoints,
  type SyncGateHarness,
} from "./useExamWorkspaceSyncGate.specSupport";

async function openEditing(harness: SyncGateHarness): Promise<void> {
  harness.gate.openExam(LINEAGE);
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

function installedAt(harness: SyncGateHarness, index: number): NativeExamDocument {
  const document = harness.installed[index];
  if (document === undefined) {
    throw new Error(`expected installed document ${index}`);
  }
  return document;
}

describe("the sync gate merge point", () => {
  it("merges exactly once on a takeover load and stores the merge", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    // The clean open installed first; only the merge installs after it.
    expect(harness.installed.length).toBe(2);
    expect(pointsOf(installedAt(harness, 1), "item_001")).toBe(7);
    expect(harness.storeCalls.length).toBe(1);
    expect(harness.storeCalls[0]).toBe(installedAt(harness, 1));
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
    documentRead.resolve(exam());
    await harness.settle();
    // The clean open installed first; the held fresh copy adds nothing.
    expect(harness.installed.length).toBe(1);
    expect(harness.mergeCalls.length).toBe(0);
    const stepRead = harness.stepReads[harness.stepReads.length - 1];
    if (stepRead === undefined) {
      throw new Error("expected a step-list read");
    }
    stepRead.resolve(undefined);
    await harness.settle();
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.installed.length).toBe(2);
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
    abandonedDocument.resolve(exam());
    await harness.settle();
    // The abandoned load stops before its step-list read.
    expect(harness.stepReads.length).toBe(1);
    expect(harness.mergeCalls.length).toBe(0);
    // Only the clean open installed; the abandoned load adds nothing.
    expect(harness.installed.length).toBe(1);
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("merges exactly once per load when a 409 lands during the merged store", async () => {
    const harness = createGate();
    await takeKept(harness);
    const store = deferred<"stored" | "failed" | "conflict">();
    harness.flags.storeBehavior = () => store.promise;
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    harness.gate.staleConflict();
    expect(harness.gate.phase.value).toBe("loading");
    store.resolve("stored");
    await harness.settle();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("keeps the kept edit until the merged store reports stored", async () => {
    const harness = createGate();
    await takeKept(harness);
    const store = deferred<"stored" | "failed" | "conflict">();
    harness.flags.storeBehavior = () => store.promise;
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    harness.flags.storeBehavior = () => Promise.resolve("stored");
    harness.gate.staleConflict();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    store.resolve("stored");
    await harness.settle();
    harness.gate.staleConflict();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("keeps the kept edit and retries the merged store after a network failure", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.flags.storeBehavior = () => Promise.resolve("failed");
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.storeCalls.length).toBe(1);
    expect(harness.pendingTimers()).toBe(1);
    expect(harness.gate.phase.value).toBe("editing");
    harness.flags.storeBehavior = () => Promise.resolve("stored");
    harness.fireTimer();
    await harness.settle();
    expect(harness.storeCalls.length).toBe(2);
    harness.gate.staleConflict();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
  });

  it("returns to loading and merges again on a 409 from the merged store", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.flags.storeBehavior = () => Promise.resolve("conflict");
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(1);
    await harness.settle();
    expect(harness.gate.phase.value).toBe("loading");
    expect(harness.documentReads.length).toBe(3);
    harness.flags.storeBehavior = () => Promise.resolve("stored");
    await succeedLoad(harness, exam());
    expect(harness.mergeCalls.length).toBe(2);
    expect(harness.gate.phase.value).toBe("editing");
  });

  it("captures the original edit plus later typing on a second refusal", async () => {
    const harness = createGate();
    await takeKept(harness);
    harness.gate.leaseAcquired();
    await succeedLoad(harness, exam());
    const merged = installedAt(harness, 1);
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
});
