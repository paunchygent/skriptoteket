/**
 * Exam workspace editing session: the typing pause after a structural edit.
 *
 * Expected behavior (TASK-SKRIPT-39-04-08 W5, TASK-SKRIPT-39-06-08 review-2 F1):
 *   Typing becomes an undo step after a 900 ms pause, also when it was typed
 *   while the owed snapshots of an earlier structural edit were still being
 *   stored; storing an owed snapshot never cancels that pause. Transport is the named double of the server's step store, slowed
 *   to a 50 ms round trip; the composables are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

const ROUND_TRIP_MS = 50;

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
  vi.useFakeTimers();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

function typed(text: string) {
  return [{ heading_level: null, segments: [{ kind: "text" as const, text, marks: [] }] }];
}

async function elapse(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

describe("typing right after a structural edit", () => {
  // Guards the typing burst's own undo step: the second owed store must not
  // cancel the pause that typing started while the first one was in flight,
  // else the text stays a pending edit and merges into whatever is stored next.
  it("still becomes its own step after the 900 ms pause", async () => {
    const baseline = exam("Original", 1);
    baseline.items[0] = newTeacherItem("item_001", 1, "ordering");
    const { editing, server } = await openEditing(api, baseline);
    const slowStore = api.storeExamWorkspaceUndoStep.getMockImplementation()!;
    api.storeExamWorkspaceUndoStep.mockImplementation(async (...args: unknown[]) => {
      await new Promise((resolve) => setTimeout(resolve, ROUND_TRIP_MS));
      return slowStore(...args);
    });
    const [first, second] = editing.workspaceDocument.value!.items[0]!.choices;

    // Pending text, then "Lägg till steg": the text and the added step are owed as two steps.
    editing.updateItemChoiceBody("item_001", first!.choice_id, typed("B"), false);
    editing.addItemOrderingStep("item_001");
    // The first owed store is in flight; the teacher types into the next step meanwhile.
    await elapse(10);
    editing.updateItemChoiceBody("item_001", second!.choice_id, typed("C"), false);

    await elapse(5000);

    expect(server.state.steps).toHaveLength(3);
    expect(editing.history.pending.value).toBe(false);
  });

  it("keeps every burst its own step across two structural edits in one turn", async () => {
    const baseline = exam("Original", 1);
    baseline.items[0] = newTeacherItem("item_001", 1, "ordering");
    const { editing, server } = await openEditing(api, baseline);
    const slowStore = api.storeExamWorkspaceUndoStep.getMockImplementation()!;
    api.storeExamWorkspaceUndoStep.mockImplementation(async (...args: unknown[]) => {
      await new Promise((resolve) => setTimeout(resolve, ROUND_TRIP_MS));
      return slowStore(...args);
    });
    const [first] = editing.workspaceDocument.value!.items[0]!.choices;

    // Pending text, then two structural edits back to back: three owed stores, each its own step.
    editing.updateItemChoiceBody("item_001", first!.choice_id, typed("B"), false);
    editing.addItemOrderingStep("item_001");
    editing.addItemOrderingStep("item_001");
    // The owed stores are in flight; the teacher types into the newest step meanwhile.
    await elapse(10);
    const last = editing.workspaceDocument.value!.items[0]!.choices.at(-1)!;
    editing.updateItemChoiceBody("item_001", last.choice_id, typed("C"), false);

    await elapse(5000);

    // Typing "B", the first added step, the second added step, then typing "C".
    expect(server.state.steps).toHaveLength(4);
    expect(editing.history.pending.value).toBe(false);
  });
});
