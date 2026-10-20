/**
 * Shared doubles for the exam workspace editing-session specs: a named
 * double of the server's step store with the same position rules as
 * exam_workspace_document_store.py and exam_workspace_undo_steps.py, and a
 * production editing session opened on it.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope, ref } from "vue";
import type { Ref } from "vue";
import type { Mock } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { mergeRefusedEdit } from "./examWorkspaceRefusedEditMerge";
import { serverExamWorkspaceStore, type ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";
import { createFencedTransport } from "./examWorkspaceFencedTransport";
import type { FenceToken } from "./examWorkspaceSyncFence";
import { readStepList } from "./useExamWorkspaceHistoryLoader";
import { useExamWorkspaceSyncGate } from "./useExamWorkspaceSyncGate";

export type EditingApiMocks = {
  getExamWorkspaceDocument: Mock;
  getExamWorkspaceHistory: Mock;
  getExamWorkspaceHistoryStep: Mock;
  moveExamWorkspaceHistoryPosition: Mock;
  storeExamWorkspaceUndoStep: Mock;
};

export const LINEAGE = "00000000-0000-4000-8000-000000000001";

export function exam(title = "Original", itemCount = 2): NativeExamDocument {
  const document: NativeExamDocument = {
    assets: [],
    document_id: LINEAGE,
    header: { tags: [] },
    instructions: [],
    items: Array.from({ length: itemCount }, (_, index) => ({
      ...newTeacherItem(`item_00${index + 1}`, index + 1, "free_text"),
      points: 2,
    })),
    origin: { kind: "created" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v10",
    title,
  };
  return document;
}

export function response(document: NativeExamDocument, cursor: string): ExamWorkspaceDocumentResponse {
  const payload: ExamWorkspaceDocumentResponse = {
    conversion: null,
    document,
    export_blockers: [],
    history_cursor: cursor,
    notes: [],
    saved_document: document,
    summary: {
      course_key: null,
      lineage_id: LINEAGE,
      name: "Prov.provdokument.zip",
      saved_at: "2026-10-17T20:00:00Z",
      title: document.title,
      vault_file_id: LINEAGE,
      version: document.revision,
    },
  };
  return payload;
}

export function conflict(): ApiError {
  return new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats sedan det öppnades.", status: 409 });
}

/** The fake server's mutable history position; the step list holds step ids in order. */
type FakeServerState = {
  cursor: string;
  position: string;
  steps: string[];
};
/** The server's history: the same position rules as exam_workspace_document_store.py and undo_steps. */
export function fakeServer(api: EditingApiMocks, baseline: NativeExamDocument) {
  let counter = 0;
  const documents = new Map<string, NativeExamDocument>([["step-0", baseline]]);
  const state: FakeServerState = {
    cursor: "step-0",
    position: "step-0",
    steps: [],
  };
  const history = () => ({
    baseline_step_id: "step-0",
    cursor: state.cursor,
    position_step_id: state.position,
    step_ids: [...state.steps],
  });
  const append = (document: NativeExamDocument) => {
    const stepId = `step-${++counter}`;
    documents.set(stepId, document);
    state.steps = [...state.steps, stepId].slice(-10);
    return stepId;
  };
  api.getExamWorkspaceHistory.mockImplementation(async () => history());
  api.getExamWorkspaceDocument.mockImplementation(async (lineageId: string) => {
    const current = documents.get(state.cursor);
    if (current === undefined) {
      throw new Error("expected the served document");
    }
    // Follow-up loads (takeover reclaim, conflict reload) read the document
    // again: serve the newest stored copy under the requested lineage.
    const payload = response(JSON.parse(JSON.stringify(current)), state.cursor);
    return {
      ...payload,
      summary: { ...payload.summary, lineage_id: lineageId, vault_file_id: lineageId },
    };
  });
  api.getExamWorkspaceHistoryStep.mockImplementation(async (_lineage: string, stepId: string) => ({
    document: documents.get(stepId)!,
    step_id: stepId,
  }));
  api.moveExamWorkspaceHistoryPosition.mockImplementation(
    async (_l: string, request: { expectedCursor: string; stepId: string }) => {
      if (request.expectedCursor !== state.cursor) throw conflict();
      state.position = request.stepId;
      state.cursor = `move-${++counter}`;
      const document = documents.get(request.stepId)!;
      return { document, export_blockers: [], history: history() };
    },
  );
  const truncateAfter = (after: string) => {
    state.steps = state.steps.slice(0, ["step-0", ...state.steps].indexOf(after));
  };
  api.storeExamWorkspaceUndoStep.mockImplementation(
    async (_l: string, request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string }) => {
      if (request.expectedCursor !== state.cursor) throw conflict();
      truncateAfter(request.afterStepId ?? state.position);
      state.cursor = append(request.document);
      state.position = state.cursor;
      return { document: request.document, export_blockers: [], history: history() };
    },
  );
  return { documents, state };
}

const scopes: ReturnType<typeof effectScope>[] = [];

/** Stop every editing session a test opened. */
export function stopScopes(): void {
  for (const scope of scopes.splice(0)) scope.stop();
}
export function inScope<T>(run: () => T): T {
  const scope = effectScope();
  scopes.push(scope);
  return scope.run(run)!;
}

export async function openEditing(api: EditingApiMocks, baseline = exam()) {
  const server = fakeServer(api, baseline);
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, {
      server: {
        claim: () =>
          Promise.resolve({
            holder_tab_id: "tab-1",
            renewed_at: "2026-10-19T12:00:00.000Z",
            takeover_requested: false,
            takeover_requested_by: null,
          }),
        release: () =>
          Promise.resolve({
            holder_tab_id: null,
            renewed_at: null,
            takeover_requested: false,
            takeover_requested_by: null,
          }),
        renew: () =>
          Promise.resolve({
            holder_tab_id: "tab-1",
            renewed_at: "2026-10-19T12:00:00.000Z",
            takeover_requested: false,
            takeover_requested_by: null,
          }),
        requestTakeover: () =>
          Promise.resolve({
            holder_tab_id: "tab-1",
            renewed_at: "2026-10-19T12:00:00.000Z",
            takeover_requested: false,
            takeover_requested_by: null,
          }),
      },
      tabId: "tab-1",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await flushPromises();
  return { editing, server };
}

/**
 * Make the fake step store answer 422 for drafts the save rules refuse, as the
 * server's `_answer_key_invariants` do: the wrapped store throws a
 * VALIDATION_ERROR instead of storing, so a refused edit stays pending and
 * undo must discard it.
 */
export function refuseSaveRefusedDrafts(api: EditingApiMocks): void {
  const inner = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (!inner) {
    throw new Error("expected the step store double");
  }
  api.storeExamWorkspaceUndoStep.mockImplementation(
    async (
      lineage: string,
      request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string },
    ) => {
      if (examWorkspaceSaveRefusalCopy(request.document) !== null) {
        throw new ApiError({
          code: "VALIDATION_ERROR",
          message: "Validation error",
          details: [],
          correlationId: null,
          status: 422,
        });
      }
      return inner(lineage, request);
    },
  );
}

/**
 * The mocked transport halves the gate-backed history harness reads through.
 */
export type GateHistoryApi = {
  getExamWorkspaceDocument: Mock;
  getExamWorkspaceHistory: Mock;
};

/**
 * Options for the gate-backed history harness (TASK-SKRIPT-40-04-14, G2).
 * Every history unit spec builds the production history against a real sync
 * gate and runs the gate's fresh load to `editing` before its test, the way
 * the editing session wires the two owners.
 */
export type GateHistoryOptions = {
  api: GateHistoryApi;
  baseline: NativeExamDocument;
  /** The cursor the served fresh document carries; defaults to `step-0`. */
  documentCursor?: string;
  /** Fail the opening step-list read once, so the gate retries it. */
  failFirstHistoryLoad?: boolean;
  isGuest?: boolean;
  shared?: ExamWorkspaceSharedStore;
  lineage?: string;
  tabId?: string;
  /** Whether this tab holds the lease when the fresh load finishes. */
  leaseHeld?: boolean;
  isBlocked?: () => boolean;
  isReplacing?: () => boolean;
  replaceCopy?: <T>(run: () => Promise<T>) => Promise<T>;
  noteStored?: (document: NativeExamDocument) => void;
  noteLeaseLost?: () => void;
  noteConflict?: () => void;
  noteReloadFailed?: () => void;
};

export type GateHistoryFixture = {
  gate: ReturnType<typeof useExamWorkspaceSyncGate>;
  history: ReturnType<typeof useExamWorkspaceHistory>;
  historyCursor: Ref<string | null>;
  leaseHeld: Ref<boolean>;
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** Run the gate's pending reload retry; throws when none is scheduled. */
  fireGateRetry: () => void;
  gateRetryPending: () => boolean;
  stop: () => void;
};

/**
 * The document response the gate's fresh load reads: the baseline served as
 * the fresh server copy under the harness lineage, so the gate's own install
 * is recognized (and consumed) like the editing session's.
 */
function gateDocumentResponse(
  document: NativeExamDocument,
  cursor: string,
  lineageId: string,
): ExamWorkspaceDocumentResponse {
  const payload = response(document, cursor);
  return { ...payload, summary: { ...payload.summary, lineage_id: lineageId } };
}

/**
 * Build the production history against a real sync gate and run the fresh
 * load to `editing`: the document GET serves the baseline, the step-list GET
 * runs the history's own load, installs track the gate's cursor like the
 * editing session, and lease loss, conflicts and the reload retry report back
 * through the gate. The cursor the gate installed itself is consumed, exactly
 * like the editing session; any other cursor starts a gate fresh load.
 */
export async function openGateHistory(options: GateHistoryOptions): Promise<GateHistoryFixture> {
  const api = options.api;
  const baseline = options.baseline;
  const lineage = options.lineage ?? "lineage-1";
  const shared = options.shared ?? serverExamWorkspaceStore.shared;
  if (options.failFirstHistoryLoad === true) {
    api.getExamWorkspaceHistory.mockRejectedValueOnce(new Error("offline"));
  }
  api.getExamWorkspaceDocument.mockImplementation(async () =>
    gateDocumentResponse(baseline, options.documentCursor ?? "step-0", lineage),
  );

  const workspaceDocument = ref<NativeExamDocument | null>(baseline);
  const historyCursor = ref<string | null>(null);
  const serverDocument = ref<NativeExamDocument | null>(null);
  const leaseHeld = ref(options.leaseHeld ?? true);
  const gateHolder: { gate: ReturnType<typeof useExamWorkspaceSyncGate> | null } = { gate: null };
  let gateCursor: { cursor: string; lineage: string } | null = null;
  const retryTimers: Array<() => void> = [];

  function requireGate(): ReturnType<typeof useExamWorkspaceSyncGate> {
    const gate = gateHolder.gate;
    if (gate === null) {
      throw new Error("expected the sync gate");
    }
    return gate;
  }

  const scope = effectScope();
  const constructed = scope.run(() => {
    const fenced = createFencedTransport(
      () => requireGate().fence,
      options.shared ?? shared,
    );
    const history = useExamWorkspaceHistory({
      historyCursor,
      install: (token: FenceToken, document: NativeExamDocument) => {
        if (!requireGate().fence.isCurrent(token)) {
          return;
        }
        workspaceDocument.value = document;
      },
      isBlocked: options.isBlocked ?? (() => false),
      enqueueWrite: (run, refused) => requireGate().enqueueWrite(run, refused),
      isCurrent: (token) => requireGate().fence.isCurrent(token),
      noteGateStored: (token: FenceToken) => requireGate().noteStored(token),
      noteInstalledCursor: (foreignLineageId, cursor) => {
        if (
          gateCursor !== null &&
          gateCursor.lineage === foreignLineageId &&
          gateCursor.cursor === cursor
        ) {
          gateCursor = null;
          return true;
        }
        requireGate().foreignCursor(true);
        return false;
      },
      isGuest: () => options.isGuest ?? false,
      keptUnstored: () => requireGate().hasKeptEdit.value,
      isReadOnly: () => gateHolder.gate?.editingLocked.value ?? true,
      isReplacing: options.isReplacing ?? (() => false),
      replaceCopy: options.replaceCopy ?? ((run) => run()),
      lineageId: () => lineage,
      noteExportBlockers: () => undefined,
      noteLeaseLost: () => {
        leaseHeld.value = false;
        requireGate().leaseLost();
        options.noteLeaseLost?.();
      },
      noteStored: (token: FenceToken, document: NativeExamDocument) => {
        if (!requireGate().fence.isCurrent(token)) {
          return;
        }
        options.noteStored?.(document);
      },
      onConflict: () => {
        requireGate().staleConflict();
        options.noteConflict?.();
        return Promise.resolve();
      },
      savedRevision: () => baseline.revision,
      transport: fenced,
      tabId: () => options.tabId ?? "tab-1",
      workspaceDocument,
    });
    const gate = useExamWorkspaceSyncGate({
      isLeaseHeld: () => leaseHeld.value,
      isOpenClaimPending: () => false,
      hasPendingEdit: () => history.pending.value,
      currentInflightDocument: () => history.inflightDocument.value,
      settleEdit: () => history.flush(true),
      currentStepDocument: () => history.stepDocument.value,
      currentWorkingCopy: () => workspaceDocument.value,
      dropOwedSnapshots: () => history.dropOwedSnapshots(),
      readDocument: (readLineageId) => shared.getExamWorkspaceDocument(readLineageId),
      readStepList: (readLineageId) => readStepList(shared, readLineageId),
      applyStepList: (token, read, base) => history.applySteps(token, read, base ?? serverDocument.value),
      resetStepList: (token) => history.resetSteps(token),
      installFresh: (token: FenceToken, fresh) => {
        if (!requireGate().fence.isCurrent(token)) {
          return;
        }
        gateCursor = { cursor: fresh.history_cursor, lineage: fresh.summary.lineage_id };
        serverDocument.value = fresh.document;
        workspaceDocument.value = fresh.document;
        historyCursor.value = fresh.history_cursor;
      },
      installMerged: (token: FenceToken, fresh, merged) => {
        if (!requireGate().fence.isCurrent(token)) {
          return;
        }
        gateCursor = { cursor: fresh.history_cursor, lineage: fresh.summary.lineage_id };
        serverDocument.value = fresh.document;
        workspaceDocument.value = merged;
        historyCursor.value = fresh.history_cursor;
      },
      replaceCopy: options.replaceCopy ?? ((run) => run()),
      requestStore: () => {
        void history.flush();
      },
      mergeRefusedEdit,
      notifyReloadFailed: () => {
        options.noteReloadFailed?.();
      },
      timer: {
        cancel: () => {
          retryTimers.length = 0;
        },
        schedule: (run) => {
          retryTimers.push(run);
        },
      },
    });
    gateHolder.gate = gate;
    return { gate, history };
  });
  if (constructed === undefined) {
    throw new Error("expected the gate-backed history");
  }
  constructed.gate.openExam(lineage, false);
  await flushPromises();
  return {
    fireGateRetry: () => {
      const next = retryTimers.shift();
      if (next === undefined) {
        throw new Error("expected a scheduled gate retry");
      }
      next();
    },
    gate: constructed.gate,
    gateRetryPending: () => retryTimers.length > 0,
    history: constructed.history,
    historyCursor,
    leaseHeld,
    stop: () => scope.stop(),
    workspaceDocument,
  };
}
