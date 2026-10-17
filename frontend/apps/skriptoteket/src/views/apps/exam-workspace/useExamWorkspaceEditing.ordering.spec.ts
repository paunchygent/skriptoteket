/**
 * Exam workspace editing session: ordering edits and undo.
 *
 * Expected behavior (TASK-SKRIPT-39-06-08 D2, D5):
 *   "Blanda om" changes the saved print order as one history step, and undo
 *   restores the print order from before it. Adding a step is one step too,
 *   and undo removes the step and its place in the print order.
 *
 * Transport is the named double of the server's step store; the composables
 * are the production ones.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { exam, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

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

function orderingExam(): NativeExamDocument {
  const baseline = exam("Original", 1);
  const ordering = newTeacherItem("item_001", 1, "ordering");
  // Four steps printed as 3, 1, 4, 2 so a shuffle has room to differ from it.
  const choices = ["choice_001", "choice_002", "choice_003", "choice_004"].map((choice_id) => ({
    ...ordering.choices[0]!,
    choice_id,
  }));
  baseline.items[0] = { ...ordering, choices, print_order: ["choice_003", "choice_001", "choice_004", "choice_002"] };
  return baseline;
}

describe("ordering edits through the editing session", () => {
  it("Blanda om is one undoable step that restores the previous print order", async () => {
    const { editing, server } = await openEditing(api, orderingExam());
    const before = [...editing.workspaceDocument.value!.items[0]!.print_order];
    // Math.random is the production source; pin it so the draw is a known non-key, non-previous order.
    const random = vi.spyOn(Math, "random").mockReturnValue(0);

    editing.shuffleItemOrderingSteps("item_001");
    random.mockRestore();
    await editing.history.flush();

    const shuffled = editing.workspaceDocument.value!.items[0]!.print_order;
    expect(shuffled).not.toEqual(before);
    expect(shuffled).not.toEqual(["choice_001", "choice_002", "choice_003", "choice_004"]);
    expect(server.state.steps).toHaveLength(1);

    await editing.history.undo();
    expect(editing.workspaceDocument.value!.items[0]!.print_order).toEqual(before);
    await editing.history.redo();
    expect(editing.workspaceDocument.value!.items[0]!.print_order).toEqual(shuffled);
  });

  it("adding a step is one undoable step", async () => {
    const { editing, server } = await openEditing(api, orderingExam());

    editing.addItemOrderingStep("item_001");
    await editing.history.flush();

    const added = editing.workspaceDocument.value!.items[0]!;
    expect(added.choices).toHaveLength(5);
    expect(added.print_order).toHaveLength(5);
    expect(server.state.steps).toHaveLength(1);

    await editing.history.undo();
    const restored = editing.workspaceDocument.value!.items[0]!;
    expect(restored.choices).toHaveLength(4);
    expect(restored.print_order).toEqual(["choice_003", "choice_001", "choice_004", "choice_002"]);
  });
});
