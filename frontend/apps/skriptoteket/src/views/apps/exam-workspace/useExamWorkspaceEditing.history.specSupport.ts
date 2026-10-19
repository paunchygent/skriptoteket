/**
 * Shared doubles for the exam workspace editing-session specs: a named
 * double of the server's step store with the same position rules as
 * exam_workspace_document_store.py and exam_workspace_undo_steps.py, and a
 * production editing session opened on it.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope } from "vue";
import type { Mock } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";

export type EditingApiMocks = {
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
    schema_version: "native_exam_document_v8",
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
