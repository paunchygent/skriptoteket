/**
 * Exam workspace editing session: AI suggestions that arrive while a
 * replacing read runs (TASK-SKRIPT-40-04-03 review 2, R2-F3).
 *
 * Expected behavior:
 *   - An AI suggestion that arrives while undo, redo or a server command
 *     (Byt frågetyp) replaces the copy is written again onto the document
 *     the read installs, so a delivered suggestion is never overwritten.
 *
 * Transport is a named double of the server's step store; the composables
 * are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { newTeacherItem } from "./examWorkspaceItemEdits";
import { keyedSuggestion } from "./examWorkspaceKeyedItems.specSupport";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { exam, openEditing, response, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

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
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(stopScopes);

describe("AI arrivals during a replacing read (R2-F3)", () => {
  const arriving = keyedSuggestion({});

  function deliver(editing: ReturnType<typeof useExamWorkspaceEditing>, itemId: string): void {
    editing.applyArrivingSuggestions(editing.openExam.value!, [{ item_id: itemId, suggestion: arriving }]);
  }

  it("a suggestion delivered while undo reads a step is kept on the step it installs", async () => {
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
    expect(editing.isBusy.value).toBe(true);
    deliver(editing, "item_001");
    release();
    await moving;

    expect(editing.workspaceDocument.value!.title).toBe("Original");
    expect(editing.workspaceDocument.value!.items[0]!.ai_suggestion).toEqual(arriving);
  });

  it("a suggestion delivered while redo reads a step is kept on the step it installs", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Steg ett");
    await editing.history.flush();
    await editing.history.undo();
    let release!: () => void;
    api.getExamWorkspaceHistoryStep.mockImplementationOnce(
      (_l: string, stepId: string) =>
        new Promise((resolve) => {
          release = () => resolve({ document: server.documents.get(stepId)!, step_id: stepId });
        }),
    );

    const moving = editing.history.redo();
    await flushPromises();
    deliver(editing, "item_002");
    release();
    await moving;

    expect(editing.workspaceDocument.value!.title).toBe("Steg ett");
    expect(editing.workspaceDocument.value!.items[1]!.ai_suggestion).toEqual(arriving);
  });

  it("a suggestion delivered while Byt frågetyp runs is kept on the command's document", async () => {
    const { editing } = await openEditing(api);
    let release!: () => void;
    api.changeExamWorkspaceItemType.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          const changed = exam();
          changed.items[0] = { ...newTeacherItem("item_001", 1, "single_choice"), points: 2 };
          release = () => resolve({ ...response(changed, "command-1"), dropped_content: [] });
        }),
    );

    const changing = editing.structure.changeType("item_001", "single_choice");
    await flushPromises();
    expect(editing.isBusy.value).toBe(true);
    deliver(editing, "item_002");
    release();
    await changing;

    expect(editing.workspaceDocument.value!.items[0]!.kind).toBe("single_choice");
    expect(editing.workspaceDocument.value!.items[1]!.ai_suggestion).toEqual(arriving);
  });
});
