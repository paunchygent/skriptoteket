/**
 * Shared doubles for the exam workspace sync-gate specs: a transport double
 * with deferred document and step-list reads, a merge spy, a manual retry
 * timer, and mutable lease and pending-edit ports.
 */

import { flushPromises } from "@vue/test-utils";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useExamWorkspaceSyncGate } from "./useExamWorkspaceSyncGate";
import { exam, LINEAGE, response } from "./useExamWorkspaceEditing.history.specSupport";

export { exam, LINEAGE, response };

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
};

export type SyncGateCounts = {
  reloadFailures: number;
  replaceCalls: number;
  owedDropped: number;
  storeRequests: number;
};

export type SyncGateHarness = {
  gate: ReturnType<typeof useExamWorkspaceSyncGate>;
  documentReads: Deferred<ExamWorkspaceDocumentResponse>[];
  stepReads: Array<{ base: NativeExamDocument | null; read: Deferred<void> }>;
  freshInstalled: ExamWorkspaceDocumentResponse[];
  mergedInstalled: NativeExamDocument[];
  mergeCalls: Array<{ base: NativeExamDocument; edited: NativeExamDocument; newest: NativeExamDocument }>;
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
  const documentReads: Deferred<ExamWorkspaceDocumentResponse>[] = [];
  const stepReads: SyncGateHarness["stepReads"] = [];
  const freshInstalled: ExamWorkspaceDocumentResponse[] = [];
  const mergedInstalled: NativeExamDocument[] = [];
  const mergeCalls: SyncGateHarness["mergeCalls"] = [];
  const counts: SyncGateCounts = { owedDropped: 0, reloadFailures: 0, replaceCalls: 0, storeRequests: 0 };
  const timers: Array<() => void> = [];
  const flags: SyncGateFlags = {
    leaseHeld: true,
    mergeResult: undefined,
    pendingEdit: false,
    stepDocument: null,
    workingCopy: null,
  };
  const gate = useExamWorkspaceSyncGate({
    currentStepDocument: () => flags.stepDocument,
    currentWorkingCopy: () => flags.workingCopy,
    dropOwedSnapshots: () => {
      counts.owedDropped += 1;
    },
    hasPendingEdit: () => flags.pendingEdit,
    installFresh: (fresh: ExamWorkspaceDocumentResponse) => {
      freshInstalled.push(fresh);
    },
    installMerged: (fresh: ExamWorkspaceDocumentResponse, merged: NativeExamDocument) => {
      void fresh;
      mergedInstalled.push(merged);
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
      const read = deferred<ExamWorkspaceDocumentResponse>();
      documentReads.push(read);
      return read.promise;
    },
    readSteps: (lineageId: string, base: NativeExamDocument | null) => {
      void lineageId;
      const read = deferred<void>();
      stepReads.push({ base, read });
      return read.promise;
    },
    replaceCopy: <T>(run: () => Promise<T>): Promise<T> => {
      counts.replaceCalls += 1;
      return run();
    },
    requestStore: () => {
      counts.storeRequests += 1;
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
    freshInstalled,
    gate,
    mergedInstalled,
    mergeCalls,
    pendingTimers: () => timers.length,
    settle: async (): Promise<void> => {
      await flushPromises();
    },
    stepReads,
  };
}

function latestDocumentRead(harness: SyncGateHarness): Deferred<ExamWorkspaceDocumentResponse> | undefined {
  return harness.documentReads[harness.documentReads.length - 1];
}

function latestStepRead(harness: SyncGateHarness): Deferred<void> | undefined {
  const latest = harness.stepReads[harness.stepReads.length - 1];
  return latest === undefined ? undefined : latest.read;
}

/** Resolve the latest document and step-list reads with fresh copies. */
export async function succeedLoad(
  harness: SyncGateHarness,
  fresh: NativeExamDocument,
): Promise<void> {
  const documentRead = latestDocumentRead(harness);
  if (documentRead !== undefined) {
    documentRead.resolve(response(fresh, "step-0"));
    await harness.settle();
  }
  const stepRead = latestStepRead(harness);
  if (stepRead === undefined) {
    throw new Error("expected a step-list read");
  }
  stepRead.resolve(undefined);
  await harness.settle();
}
