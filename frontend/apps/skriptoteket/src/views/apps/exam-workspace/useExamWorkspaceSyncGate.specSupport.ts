/**
 * Shared doubles for the exam workspace sync-gate specs: a transport double
 * with deferred document and step-list reads, a merge spy, a manual retry
 * timer, and mutable lease and copy ports.
 */

import { flushPromises } from "@vue/test-utils";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useExamWorkspaceSyncGate } from "./useExamWorkspaceSyncGate";
import type { FenceToken } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceStepListRead } from "./useExamWorkspaceHistoryLoader";
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
  /** An open claim is still in flight; a finished fresh load then keeps `loading`. */
  claimPending: boolean;
  /** The confirmed copy C the write boundary stands on. */
  confirmedCopy: NativeExamDocument | null;
  /** The desired copy D in front of the teacher. */
  desiredCopy: NativeExamDocument | null;
  /** The unresolved published pieces: U plus the active attempt's pieces. */
  publishedPieces: Set<string>;
  /** The merge spy's result; undefined falls back to the fresh copy with 7 points. */
  mergeResult: NativeExamDocument | undefined;
};

export type SyncGateCounts = {
  reloadFailures: number;
  replaceCalls: number;
  owedDropped: number;
  storeRequests: number;
  abandonedAttempts: number;
  unconfirmedResets: number;
};

export type SyncGateHarness = {
  gate: ReturnType<typeof useExamWorkspaceSyncGate>;
  documentReads: Deferred<ExamWorkspaceDocumentResponse>[];
  stepReads: Array<{ read: Deferred<ExamWorkspaceStepListRead> }>;
  freshInstalled: ExamWorkspaceDocumentResponse[];
  mergedInstalled: NativeExamDocument[];
  appliedSteps: Array<{ base: NativeExamDocument | null; read: ExamWorkspaceStepListRead }>;
  stepResets: () => number;
  mergeCalls: Array<{ desired: NativeExamDocument; owned: ReadonlySet<string>; newest: NativeExamDocument }>;
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
  const appliedSteps: SyncGateHarness["appliedSteps"] = [];
  let stepResets = 0;
  const counts: SyncGateCounts = {
    abandonedAttempts: 0,
    owedDropped: 0,
    reloadFailures: 0,
    replaceCalls: 0,
    storeRequests: 0,
    unconfirmedResets: 0,
  };
  const timers: Array<() => void> = [];
  const flags: SyncGateFlags = {
    claimPending: false,
    confirmedCopy: null,
    desiredCopy: null,
    leaseHeld: true,
    mergeResult: undefined,
    publishedPieces: new Set(),
  };
  const gate = useExamWorkspaceSyncGate({
    abandonAttempt: () => {
      counts.abandonedAttempts += 1;
    },
    confirmedCopy: () => flags.confirmedCopy,
    desiredCopy: () => flags.desiredCopy,
    dropOwedSnapshots: () => {
      counts.owedDropped += 1;
    },
    installFresh: (token: FenceToken, fresh: ExamWorkspaceDocumentResponse) => {
      void token;
      flags.confirmedCopy = fresh.document;
      flags.desiredCopy = fresh.document;
      freshInstalled.push(fresh);
    },
    installMerged: (token: FenceToken, fresh: ExamWorkspaceDocumentResponse, merged: NativeExamDocument) => {
      void fresh;
      void token;
      flags.confirmedCopy = fresh.document;
      flags.desiredCopy = merged;
      mergedInstalled.push(merged);
    },
    isLeaseHeld: () => flags.leaseHeld,
    isOpenClaimPending: () => flags.claimPending,
    mergeRefusedEdit: (desired, owned, newest) => {
      mergeCalls.push({ desired, newest, owned });
      if (flags.mergeResult !== undefined) {
        return flags.mergeResult;
      }
      return withPoints(newest, 7);
    },
    notifyReloadFailed: () => {
      counts.reloadFailures += 1;
    },
    publishedPieces: () => new Set(flags.publishedPieces),
    readDocument: (lineageId: string) => {
      void lineageId;
      const read = deferred<ExamWorkspaceDocumentResponse>();
      documentReads.push(read);
      return read.promise;
    },
    readStepList: (lineageId: string) => {
      void lineageId;
      const read = deferred<ExamWorkspaceStepListRead>();
      stepReads.push({ read });
      return read.promise;
    },
    applyStepList: (token: FenceToken, read: ExamWorkspaceStepListRead, base: NativeExamDocument | null) => {
      void token;
      if (base !== null) {
        flags.confirmedCopy = base;
      }
      appliedSteps.push({ base, read });
    },
    resetStepList: (token: FenceToken) => {
      void token;
      stepResets += 1;
    },
    replaceCopy: <T>(run: () => Promise<T>): Promise<T> => {
      counts.replaceCalls += 1;
      return run();
    },
    requestStore: () => {
      counts.storeRequests += 1;
    },
    resetUnconfirmed: () => {
      counts.unconfirmedResets += 1;
    },
    settleEdit: () => Promise.resolve(true),
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
    appliedSteps,
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
    stepResets: () => stepResets,
  };
}

function latestDocumentRead(harness: SyncGateHarness): Deferred<ExamWorkspaceDocumentResponse> | undefined {
  return harness.documentReads[harness.documentReads.length - 1];
}

function latestStepRead(harness: SyncGateHarness): Deferred<ExamWorkspaceStepListRead> | undefined {
  const latest = harness.stepReads[harness.stepReads.length - 1];
  return latest === undefined ? undefined : latest.read;
}

/** A parsed step-list read standing on `position`. */
export function stepListRead(position = "step-0", stepIds: string[] = []): ExamWorkspaceStepListRead {
  return { baselineId: "step-0", position, stepIds: [...stepIds] };
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
  stepRead.resolve(stepListRead());
  await harness.settle();
}
