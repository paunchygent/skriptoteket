/**
 * Exam workspace editing session: undo history across Spara, failed
 * prerequisite stores, and edits while a replacing read runs.
 *
 * Expected behavior (TASK-SKRIPT-40-04-03 review 1, F1-F4):
 *   - After Spara the cursor names no step, yet undo and redo still move
 *     between the retained steps, because the editor stands on the server's
 *     `position_step_id`, not on the cursor.
 *   - When the pending edit cannot be stored, a replacing command (Byt
 *     frågetyp) and undo do not run, and the pending edit stays.
 *   - While undo reads a step, editing and structure commands are refused,
 *     so nothing typed meanwhile is lost when the step arrives.
 *   - The exam's only question cannot be deleted; the refusal is inline.
 *
 * Transport is a named double of the server's step store; the composables
 * are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

const LINEAGE = "00000000-0000-4000-8000-000000000001";

function exam(title = "Original", itemCount = 2): NativeExamDocument {
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

function response(document: NativeExamDocument, cursor: string): ExamWorkspaceDocumentResponse {
  return {
    conversion: null,
    document,
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

function withoutRevision(document: NativeExamDocument): string {
  return JSON.stringify({ ...document, revision: 0 });
}

/** The server's history: the same position rules as exam_workspace_document_store.py and undo_steps. */
function fakeServer(baseline: NativeExamDocument) {
  let counter = 0;
  const documents = new Map<string, NativeExamDocument>([["step-0", baseline]]);
  const state = {
    cursor: "step-0",
    position: "step-0" as string | null,
    saved: baseline,
    steps: [] as string[],
  };
  const history = () => ({
    baseline_step_id: "step-0",
    cursor: state.cursor,
    position_step_id: state.position,
    step_ids: [...state.steps],
  });
  const newest = () => state.steps[state.steps.length - 1] ?? "step-0";
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
  api.storeExamWorkspaceUndoStep.mockImplementation(
    async (_l: string, request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string }) => {
      if (request.expectedCursor !== state.cursor) throw Object.assign(new Error("conflict"), { status: 409 });
      if (request.afterStepId !== null) {
        state.steps = state.steps.slice(0, ["step-0", ...state.steps].indexOf(request.afterStepId));
      } else if (withoutRevision(documents.get(newest())!) !== withoutRevision(state.saved)) {
        append(state.saved);
      }
      state.cursor = append(request.document);
      state.position = state.cursor;
      return { document: request.document, history: history() };
    },
  );
  api.saveExamWorkspaceDocument.mockImplementation(async (_l: string, request: { document: NativeExamDocument }) => {
    state.saved = request.document;
    state.cursor = `saved-${++counter}`;
    const same = withoutRevision(documents.get(newest())!) === withoutRevision(request.document);
    state.position = same ? newest() : null;
    return response(request.document, state.cursor);
  });
  return { documents, state };
}

const scopes: ReturnType<typeof effectScope>[] = [];
function inScope<T>(run: () => T): T {
  const scope = effectScope();
  scopes.push(scope);
  return scope.run(run)!;
}

async function openEditing(baseline = exam()) {
  const server = fakeServer(baseline);
  const editing = inScope(() => useExamWorkspaceEditing());
  editing.applyCommandResponse(response(baseline, "step-0"));
  await flushPromises();
  return { editing, server };
}

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  for (const scope of scopes.splice(0)) scope.stop();
});

describe("undo history across Spara (F1)", () => {
  it("keeps undo and redo after Spara rotates the cursor to an id that is no step", async () => {
    const { editing, server } = await openEditing();
    editing.setCourse(null);
    editing.setTitle("Lärarens rubrik");
    expect(await editing.save()).toBe(true);
    await flushPromises();

    expect(server.state.steps).not.toContain(server.state.cursor);
    expect(editing.history.canUndo.value).toBe(true);
    await editing.history.undo();
    expect(editing.workspaceDocument.value!.title).toBe("Original");
    expect(editing.history.canRedo.value).toBe(true);
    await editing.history.redo();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens rubrik");
  });

  it("reopened after Spara, the editor stands on the saved step and can undo", async () => {
    const first = await openEditing();
    first.editing.setTitle("Sparad rubrik");
    await first.editing.save();
    await flushPromises();
    const saved = first.editing.workspaceDocument.value!;

    const workspaceDocument = ref<NativeExamDocument | null>(saved);
    const history = inScope(() =>
      useExamWorkspaceHistory({
        historyCursor: ref(first.server.state.cursor),
        install: (document) => {
          workspaceDocument.value = document;
        },
        isBlocked: () => false,
        isCommandRunning: () => false,
        lineageId: () => LINEAGE,
        onConflict: vi.fn(async () => undefined),
        savedRevision: () => saved.revision,
        serverDocument: ref(saved),
        workspaceDocument,
      }),
    );
    await flushPromises();
    expect(history.canUndo.value).toBe(true);
    await history.undo();
    expect(workspaceDocument.value!.title).toBe("Original");
  });

  it("a Spara no step holds is retained before the next edit, so undo returns to it", async () => {
    const { editing, server } = await openEditing();
    // The autosave of this title fails, so Spara writes a copy no step holds.
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Bara sparad");
    expect(await editing.save()).toBe(true);
    await flushPromises();
    expect(server.state.position).toBeNull();
    expect(editing.history.canUndo.value).toBe(false);

    editing.setTitle("Efter Spara");
    await editing.history.flush();
    expect(api.storeExamWorkspaceUndoStep.mock.lastCall![1].afterStepId).toBeNull();
    await editing.history.undo();
    expect(editing.workspaceDocument.value!.title).toBe("Bara sparad");
  });
});

describe("a failed prerequisite store (F2)", () => {
  it("does not run Byt frågetyp and keeps the pending edit", async () => {
    const { editing } = await openEditing();
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Lärarens osparade text");

    await editing.structure.changeType("item_001", "single_choice");

    expect(api.changeExamWorkspaceItemType).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens osparade text");
    expect(editing.workspaceDocument.value!.items[0]!.kind).toBe("free_text");
    expect(toast.failure).toHaveBeenCalledOnce();
  });

  it("does not undo past a pending edit it could not store", async () => {
    const { editing } = await openEditing();
    editing.setCourse(null);
    await flushPromises();
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Lärarens osparade text");

    await editing.history.undo();

    expect(api.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens osparade text");
  });
});

describe("editing while undo reads a step (F4)", () => {
  it("refuses edits and commands until the replacing step has arrived", async () => {
    const { editing, server } = await openEditing();
    editing.setTitle("Steg ett");
    await editing.history.flush();
    let release!: () => void;
    api.getExamWorkspaceHistoryStep.mockImplementationOnce(
      (_l: string, stepId: string) =>
        new Promise((resolve) => {
          release = () => resolve({ document: server.documents.get(stepId)!, step_id: stepId });
        }),
    );

    const moving = editing.history.undo();
    await flushPromises();
    expect(api.getExamWorkspaceHistoryStep).toHaveBeenCalledOnce();
    expect(editing.isBusy.value).toBe(true);
    editing.setTitle("Skrivet medan ångra laddade");
    await editing.structure.changeType("item_001", "single_choice");
    expect(editing.workspaceDocument.value!.title).toBe("Steg ett");
    expect(api.changeExamWorkspaceItemType).not.toHaveBeenCalled();

    release();
    await moving;
    expect(editing.workspaceDocument.value!.title).toBe("Original");
    expect(editing.isBusy.value).toBe(false);
    editing.setTitle("Efter ångra");
    expect(editing.workspaceDocument.value!.title).toBe("Efter ångra");
  });
});

describe("deleting the only question (F3)", () => {
  it("is refused inline and leaves the exam and its history intact", async () => {
    const { editing } = await openEditing(exam("Original", 1));

    editing.structure.deleteItem("item_001");
    await flushPromises();

    expect(editing.workspaceDocument.value!.items).toHaveLength(1);
    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(editing.structure.deleteNotice.value).toEqual({
      kind: "refused",
      text: "Provet måste ha minst en fråga.",
    });
    expect(toast.failure).not.toHaveBeenCalled();
  });
});
