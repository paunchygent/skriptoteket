/**
 * Exam workspace editing session: undo history across Spara, failed
 * prerequisite stores, and edits while a replacing read runs.
 *
 * Expected behavior (TASK-SKRIPT-40-04-03 review 1, F1-F4; review 2, R2-F1, R2-F2):
 *   - After Spara the cursor names no step, yet undo and redo still move
 *     between the retained steps, because the editor stands on the server's
 *     `position_step_id`, not on the cursor.
 *   - When the pending edit cannot be stored, a replacing command (Byt
 *     frågetyp) and undo do not run, and the pending edit stays.
 *   - While undo reads a step, editing and structure commands are refused,
 *     so nothing typed meanwhile is lost when the step arrives.
 *   - Spara sends the step the editor stands on. The server keeps the saved
 *     copy there, or appends it as the next step when no step holds it (a
 *     failed autosave), so undo, redo and reopening work at once, and equal
 *     steps keep their own undo and redo neighbors.
 *   - The exam's only question cannot be deleted; the refusal is inline.
 *
 * Transport is a named double of the server's step store; the composables
 * are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";
import {
  conflict,
  exam,
  inScope,
  LINEAGE,
  openEditing,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
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
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(stopScopes);

describe("undo history across Spara (F1)", () => {
  it("keeps undo and redo after Spara rotates the cursor to an id that is no step", async () => {
    const { editing, server } = await openEditing(api);
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

  it("keeps undo and redo after an undo followed by Spara", async () => {
    const { editing } = await openEditing(api);
    editing.setTitle("Ett");
    await editing.history.flush();
    editing.setTitle("Två");
    await editing.history.flush();
    await editing.history.undo();
    expect(editing.workspaceDocument.value!.title).toBe("Ett");

    expect(await editing.save()).toBe(true);
    await flushPromises();

    expect(editing.history.canUndo.value).toBe(true);
    expect(editing.history.canRedo.value).toBe(true);
    await editing.history.redo();
    expect(editing.workspaceDocument.value!.title).toBe("Två");
    await editing.history.undo();
    await editing.history.undo();
    expect(editing.workspaceDocument.value!.title).toBe("Original");
  });

  it("reopened after Spara, the editor stands on the saved step and can undo", async () => {
    const first = await openEditing(api);
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
        isReplacing: () => false,
        replaceCopy: (run) => run(),
        lineageId: () => LINEAGE,
        noteExportBlockers: vi.fn(),
        onConflict: vi.fn(async () => undefined),
        savedRevision: () => saved.revision,
        serverDocument: ref(saved),
        shared: serverExamWorkspaceStore.shared,
        workspaceDocument,
      }),
    );
    await flushPromises();
    expect(history.canUndo.value).toBe(true);
    await history.undo();
    expect(workspaceDocument.value!.title).toBe("Original");
  });

  it("R2-F1: a Spara whose autosave failed is navigable at once, as the redo state and after reopening", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Autosparad");
    await editing.history.flush();
    // The autosave of this title fails, so Spara writes a copy no step holds.
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Bara sparad");
    expect(await editing.save()).toBe(true);
    await flushPromises();

    expect(server.state.steps).toHaveLength(2);
    expect(server.state.position).toBe(server.state.steps[1]);
    expect(editing.history.canUndo.value).toBe(true);
    await editing.history.undo();
    expect(editing.workspaceDocument.value!.title).toBe("Autosparad");
    expect(editing.history.canRedo.value).toBe(true);
    await editing.history.redo();
    expect(editing.workspaceDocument.value!.title).toBe("Bara sparad");

    // Reopened, the editor stands on the saved copy and undo still reaches the autosave.
    const saved = editing.workspaceDocument.value!;
    const workspaceDocument = ref<NativeExamDocument | null>(saved);
    const reopened = inScope(() =>
      useExamWorkspaceHistory({
        historyCursor: ref(server.state.cursor),
        install: (document) => {
          workspaceDocument.value = document;
        },
        isBlocked: () => false,
        isReplacing: () => false,
        replaceCopy: (run) => run(),
        lineageId: () => LINEAGE,
        noteExportBlockers: vi.fn(),
        onConflict: vi.fn(async () => undefined),
        savedRevision: () => saved.revision,
        serverDocument: ref(saved),
        shared: serverExamWorkspaceStore.shared,
        workspaceDocument,
      }),
    );
    await flushPromises();
    expect(reopened.canUndo.value).toBe(true);
    await reopened.undo();
    expect(workspaceDocument.value!.title).toBe("Autosparad");
  });
});

describe("Spara among equal steps (R2-F2)", () => {
  it("keeps the step the teacher stands on, so redo after A -> B -> A -> C and Spara at the first A shows B", async () => {
    const { editing, server } = await openEditing(api);
    for (const title of ["A", "B", "A", "C"]) {
      editing.setTitle(title);
      await editing.history.flush();
    }
    const firstA = server.state.steps[0];
    await editing.history.undo();
    await editing.history.undo();
    await editing.history.undo();
    expect(editing.workspaceDocument.value!.title).toBe("A");

    expect(await editing.save()).toBe(true);
    await flushPromises();

    expect(api.saveExamWorkspaceDocument.mock.lastCall![1].positionStepId).toBe(firstA);
    expect(server.state.position).toBe(firstA);
    await editing.history.redo();
    expect(editing.workspaceDocument.value!.title).toBe("B");
    await editing.history.undo();
    await editing.history.undo();
    expect(editing.workspaceDocument.value!.title).toBe("Original");
  });
});

describe("a failed prerequisite store (F2)", () => {
  it("does not run Byt frågetyp and keeps the pending edit", async () => {
    const { editing } = await openEditing(api);
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Lärarens osparade text");

    await editing.structure.changeType("item_001", "single_choice");

    expect(api.changeExamWorkspaceItemType).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens osparade text");
    expect(editing.workspaceDocument.value!.items[0]!.kind).toBe("free_text");
    expect(toast.failure).toHaveBeenCalledOnce();
  });

  it("does not undo past a pending edit it could not store", async () => {
    const { editing } = await openEditing(api);
    editing.setCourse(null);
    await flushPromises();
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Lärarens osparade text");

    await editing.history.undo();

    expect(api.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens osparade text");
  });
});

describe("conflict recovery under the replacing lock", () => {
  it("reloads the exam when a server command meets a newer cursor", async () => {
    const { editing } = await openEditing(api);
    api.changeExamWorkspaceItemType.mockRejectedValueOnce(conflict());
    api.getExamWorkspaceDocument.mockResolvedValueOnce(response(exam("Från en annan flik"), "other-tab"));

    await editing.structure.changeType("item_001", "single_choice");

    expect(api.getExamWorkspaceDocument).toHaveBeenCalledOnce();
    expect(editing.workspaceDocument.value!.title).toBe("Från en annan flik");
  });

  it("reloads the exam when undo's store of the pending edit meets a newer cursor", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Ett");
    await editing.history.flush();
    server.state.cursor = "other-tab";
    api.getExamWorkspaceDocument.mockResolvedValueOnce(response(exam("Från en annan flik"), "other-tab"));
    editing.setTitle("Osparad");

    await editing.history.undo();

    expect(api.getExamWorkspaceDocument).toHaveBeenCalledOnce();
    expect(api.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Från en annan flik");
  });
});

describe("editing while undo reads a step (F4)", () => {
  it("refuses edits and commands until the replacing step has arrived", async () => {
    const { editing, server } = await openEditing(api);
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
    const { editing } = await openEditing(api, exam("Original", 1));

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
