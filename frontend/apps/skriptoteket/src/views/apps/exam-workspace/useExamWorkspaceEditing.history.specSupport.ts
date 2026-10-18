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
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";

export type EditingApiMocks = {
  getExamWorkspaceHistory: Mock;
  getExamWorkspaceHistoryStep: Mock;
  saveExamWorkspaceDocument: Mock;
  storeExamWorkspaceUndoStep: Mock;
};

export const LINEAGE = "00000000-0000-4000-8000-000000000001";

export function exam(title = "Original", itemCount = 2): NativeExamDocument {
  return {
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
    schema_version: "native_exam_document_v6",
    title,
  } as NativeExamDocument;
}

export function response(document: NativeExamDocument, cursor: string): ExamWorkspaceDocumentResponse {
  return {
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
  } as ExamWorkspaceDocumentResponse;
}

export function conflict(): ApiError {
  return new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats sedan det öppnades.", status: 409 });
}

function withoutRevision(document: NativeExamDocument): string {
  return JSON.stringify({ ...document, revision: 0 });
}

/** The server's history: the same position rules as exam_workspace_document_store.py and undo_steps. */
export function fakeServer(api: EditingApiMocks, baseline: NativeExamDocument) {
  let counter = 0;
  const documents = new Map<string, NativeExamDocument>([["step-0", baseline]]);
  const state = {
    cursor: "step-0",
    position: "step-0",
    saved: baseline,
    steps: [] as string[],
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
  api.saveExamWorkspaceDocument.mockImplementation(
    async (_l: string, request: { document: NativeExamDocument; positionStepId: string }) => {
      state.saved = request.document;
      const snapshots = ["step-0", ...state.steps];
      const at = snapshots.includes(request.positionStepId) ? request.positionStepId : snapshots[snapshots.length - 1]!;
      // The saved copy stays at the editor's position; a copy no step holds becomes the next step.
      if (withoutRevision(documents.get(at)!) === withoutRevision(request.document)) {
        state.position = at;
      } else {
        truncateAfter(at);
        state.position = append(request.document);
      }
      state.cursor = `saved-${++counter}`;
      return response(request.document, state.cursor);
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
  const editing = inScope(() => useExamWorkspaceEditing());
  editing.applyCommandResponse(response(baseline, "step-0"));
  await flushPromises();
  return { editing, server };
}
