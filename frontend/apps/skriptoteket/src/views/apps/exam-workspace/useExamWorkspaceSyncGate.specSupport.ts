/**
 * Shared doubles for the exam workspace sync-gate specs: a transport double
 * with deferred document and step-list reads, a controllable merged store, a
 * merge spy, a manual retry timer, and mutable lease and pending-edit ports.
 */

import { flushPromises } from "@vue/test-utils";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  useExamWorkspaceSyncGate,
  type ExamWorkspaceSyncGateStoreOutcome,
} from "./useExamWorkspaceSyncGate";
import { exam, LINEAGE } from "./useExamWorkspaceEditing.history.specSupport";

export { exam, LINEAGE };

export type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
};

export function deferred<T>(): Deferred<T> {
  let resolveFn: ((value: T) => void) | null = null;
  let rejectFn: ((error: unknown) => void) | null = null;
  const promise = new Promise<T>((resolve, reject) => {
    resolveFn = resolve;
    rejectFn = reject;
  });
  return {
    promise,
    reject: (error: unknown) => {
      if (rejectFn !== null) {
        rejectFn(error);
      }
    },
    resolve: (value: T) => {
      if (resolveFn !== null) {
        resolveFn(value);
      }
    },
  };
}

export type SyncGateFlags = {
  leaseHeld: boolean;
  pendingEdit: boolean;
  stepDocument: NativeExamDocument | null;
  workingCopy: NativeExamDocument | null;
  /** The merge spy's result; undefined falls back to the fresh copy with 7 points. */
  mergeResult: NativeExamDocument | null | undefined;
  storeBehavior: (merged: NativeExamDocument) => Promise<ExamWorkspaceSyncGateStoreOutcome>;
};

export type SyncGateCounts = {
  reloadFailures: number;
  replaceCalls: number;
  owedDropped: number;
};

export type SyncGateHarness = {
  gate: ReturnType<typeof useExamWorkspaceSyncGate>;
  documentReads: Deferred<NativeExamDocument>[];
  stepReads: Deferred<void>[];
  installed: NativeExamDocument[];
  mergeCalls: Array<{ base: NativeExamDocument; edited: NativeExamDocument; newest: NativeExamDocument }>;
  storeCalls: NativeExamDocument[];
  counts: SyncGateCounts;
  flags: SyncGateFlags;
  fireTimer: () => void;
  pendingTimers: () => number;
  settle: () => Promise<void>;
};

export function withPoints(document: NativeExamDocument, points: number): NativeExamDocument {
  return {
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_001" ? { ...item, points } : item,
    ),
  };
}

export function pointsOf(document: NativeExamDocument, itemId: string): number | null {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

export function createGate(): SyncGateHarness {
  const documentReads: Deferred<NativeExamDocument>[] = [];
  const stepReads: Deferred<void>[] = [];
  const installed: NativeExamDocument[] = [];
  const mergeCalls: SyncGateHarness["mergeCalls"] = [];
  const storeCalls: NativeExamDocument[] = [];
  const counts: SyncGateCounts = { owedDropped: 0, reloadFailures: 0, replaceCalls: 0 };
  const timers: Array<() => void> = [];
  const flags: SyncGateFlags = {
    leaseHeld: true,
    mergeResult: undefined,
    pendingEdit: false,
    stepDocument: null,
    storeBehavior: () => Promise.resolve("stored"),
    workingCopy: null,
  };
  const gate = useExamWorkspaceSyncGate({
    currentStepDocument: () => flags.stepDocument,
    currentWorkingCopy: () => flags.workingCopy,
    dropOwedSnapshots: () => {
      counts.owedDropped += 1;
    },
    hasPendingEdit: () => flags.pendingEdit,
    installDocument: (document: NativeExamDocument) => {
      installed.push(document);
    },
    isLeaseHeld: () => flags.leaseHeld,
    mergeRefusedEdit: (base, edited, newest) => {
      mergeCalls.push({ base, edited, newest });
      if (flags.mergeResult !== undefined) {
        return flags.mergeResult;
      }
      return withPoints(newest, 7);
    },
    notifyReloadFailed: () => {
      counts.reloadFailures += 1;
    },
    readDocument: (lineageId: string) => {
      void lineageId;
      const read = deferred<NativeExamDocument>();
      documentReads.push(read);
      return read.promise;
    },
    readSteps: (lineageId: string) => {
      void lineageId;
      const read = deferred<void>();
      stepReads.push(read);
      return read.promise;
    },
    replaceCopy: <T>(run: () => Promise<T>): Promise<T> => {
      counts.replaceCalls += 1;
      return run();
    },
    storeMerged: (merged: NativeExamDocument) => {
      storeCalls.push(merged);
      return flags.storeBehavior(merged);
    },
    timer: {
      cancel: () => {
        timers.length = 0;
      },
      schedule: (run: () => void) => {
        timers.push(run);
      },
    },
  });
  return {
    counts,
    documentReads,
    fireTimer: () => {
      const next = timers.shift();
      if (next === undefined) {
        throw new Error("expected a scheduled retry");
      }
      next();
    },
    flags,
    gate,
    installed,
    mergeCalls,
    pendingTimers: () => timers.length,
    settle: async (): Promise<void> => {
      await flushPromises();
    },
    stepReads,
    storeCalls,
  };
}

/** Resolve the latest document and step-list reads with fresh copies. */
export async function succeedLoad(
  harness: SyncGateHarness,
  fresh: NativeExamDocument,
): Promise<void> {
  const documentRead = harness.documentReads[harness.documentReads.length - 1];
  if (documentRead !== undefined) {
    documentRead.resolve(fresh);
    await harness.settle();
  }
  const stepRead = harness.stepReads[harness.stepReads.length - 1];
  if (stepRead === undefined) {
    throw new Error("expected a step-list read");
  }
  stepRead.resolve(undefined);
  await harness.settle();
}
