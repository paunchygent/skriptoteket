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
  moveExamWorkspaceHistoryPosition: vi.fn(),
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

  it("typing still waiting for its pause stays when Blanda om right after it is undone", async () => {
    // Review-1 F1: the pending text and the shuffle used to become one step, so undo lost the text.
    const { editing, server } = await openEditing(api, orderingExam());
    const before = [...editing.workspaceDocument.value!.items[0]!.print_order];
    const typed = [{ heading_level: null, segments: [{ kind: "text" as const, text: "Tes", marks: [] }] }];

    editing.updateItemChoiceBody("item_001", "choice_001", typed, false);
    const random = vi.spyOn(Math, "random").mockReturnValue(0);
    editing.shuffleItemOrderingSteps("item_001");
    random.mockRestore();
    await editing.history.flush();

    const shuffled = editing.workspaceDocument.value!.items[0]!.print_order;
    expect(shuffled).not.toEqual(before);
    expect(server.state.steps).toHaveLength(2);

    await editing.history.undo();
    const undone = editing.workspaceDocument.value!.items[0]!;
    expect(undone.print_order).toEqual(before);
    expect(undone.choices[0]!.body).toEqual(typed);

    await editing.history.undo();
    expect(editing.workspaceDocument.value!.items[0]!.choices[0]!.body).not.toEqual(typed);

    await editing.history.redo();
    await editing.history.redo();
    const redone = editing.workspaceDocument.value!.items[0]!;
    expect(redone.print_order).toEqual(shuffled);
    expect(redone.choices[0]!.body).toEqual(typed);
  });

  it("a failed store of the typing before Blanda om keeps both in one step once writes work", async () => {
    // TK2: after a failed store the owed backlog is dropped, so the next
    // store sends the newest working copy: the typing and the shuffle arrive
    // as one step, and neither is lost.
    const { editing, server } = await openEditing(api, orderingExam());
    const before = [...editing.workspaceDocument.value!.items[0]!.print_order];
    const typed = [{ heading_level: null, segments: [{ kind: "text" as const, text: "Tes", marks: [] }] }];
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));

    editing.updateItemChoiceBody("item_001", "choice_001", typed, false);
    const random = vi.spyOn(Math, "random").mockReturnValue(0);
    editing.shuffleItemOrderingSteps("item_001");
    random.mockRestore();
    const shuffled = [...editing.workspaceDocument.value!.items[0]!.print_order];

    // The shuffle waits behind the failed typing store instead of being stored past it.
    expect(server.state.steps).toHaveLength(0);
    expect(await editing.history.flush()).toBe(true);
    expect(server.state.steps).toHaveLength(1);

    // The single step carries both the text and the shuffle.
    const stored = server.documents.get(server.state.cursor);
    if (stored === undefined) {
      throw new Error("expected the stored step");
    }
    expect(stored.items[0]!.print_order).toEqual(shuffled);
    expect(stored.items[0]!.choices[0]!.body).toEqual(typed);

    await editing.history.undo();
    const undone = editing.workspaceDocument.value!.items[0]!;
    expect(undone.print_order).toEqual(before);
    expect(undone.choices[0]!.body).not.toEqual(typed);

    await editing.history.redo();
    const redone = editing.workspaceDocument.value!.items[0]!;
    expect(redone.print_order).toEqual(shuffled);
    expect(redone.choices[0]!.body).toEqual(typed);
  });

  it("undo while the typing before Blanda om cannot be stored keeps the text and the shuffle in one step", async () => {
    // TK2: the failed flush drops the owed backlog; the next undo stores the
    // newest copy as one step and then takes it back, so nothing is lost.
    const { editing, server } = await openEditing(api, orderingExam());
    const typed = [{ heading_level: null, segments: [{ kind: "text" as const, text: "Tes", marks: [] }] }];
    // The shuffle's own background store meets the first failure and drops
    // the backlog; undo's flush meets the second and stops.
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline")).mockRejectedValueOnce(new Error("offline"));

    editing.updateItemChoiceBody("item_001", "choice_001", typed, false);
    const random = vi.spyOn(Math, "random").mockReturnValue(0);
    editing.shuffleItemOrderingSteps("item_001");
    random.mockRestore();
    const shuffled = [...editing.workspaceDocument.value!.items[0]!.print_order];

    // The failure hits undo's own flush; undo stops instead of storing anything.
    await editing.history.undo();
    expect(server.state.steps).toHaveLength(0);
    const kept = editing.workspaceDocument.value!.items[0]!;
    expect(kept.print_order).toEqual(shuffled);
    expect(kept.choices[0]!.body).toEqual(typed);

    // Writes work again: the next undo stores the newest copy as one step,
    // then takes it back.
    await editing.history.undo();
    expect(server.state.steps).toHaveLength(1);
    const lastStore = api.storeExamWorkspaceUndoStep.mock.calls.at(-1);
    if (lastStore === undefined) {
      throw new Error("expected a stored step");
    }
    expect(lastStore[1].document.items[0]!.print_order).toEqual(shuffled);
    expect(lastStore[1].document.items[0]!.choices[0]!.body).toEqual(typed);

    // Nothing is lost: redo restores the text and the shuffle together.
    await editing.history.redo();
    const redone = editing.workspaceDocument.value!.items[0]!;
    expect(redone.print_order).toEqual(shuffled);
    expect(redone.choices[0]!.body).toEqual(typed);
  });

  it("a structural edit with nothing pending stores exactly one step", async () => {
    const { editing, server } = await openEditing(api, orderingExam());
    // Two pinned draws that give two different print orders, so each shuffle is a real change.
    const random = vi.spyOn(Math, "random").mockReturnValue(0);
    editing.shuffleItemOrderingSteps("item_001");
    random.mockReturnValue(0.99);
    editing.shuffleItemOrderingSteps("item_001");
    random.mockRestore();
    await editing.history.flush();

    expect(server.state.steps).toHaveLength(2);
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
