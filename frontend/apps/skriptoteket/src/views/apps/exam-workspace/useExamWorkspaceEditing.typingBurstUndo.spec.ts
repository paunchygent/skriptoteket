/**
 * Exam workspace editing session: one typing burst stays one undo step across
 * a structural acknowledgement (TASK-SKRIPT-39-06-08 tail review T1).
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 item 1 / Q2):
 *   Structural draining and store acknowledgements must not close a newer
 *   typing burst: the burst keeps its 900 ms pause and its one-step undo
 *   grouping. Typing C and then D 190 ms later in the same burst stores once,
 *   so one undo takes back CD together.
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

function choiceText(choice: {
  body: Array<{ segments: Array<{ kind: string; text?: string }> }>;
}): string {
  return choice.body
    .flatMap((paragraph) => paragraph.segments)
    .map((segment) => (segment.kind === "text" ? (segment.text ?? "") : ""))
    .join("");
}

async function elapse(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

describe("one typing burst across a structural acknowledgement", () => {
  it("stores C and D together, so one undo takes back CD", async () => {
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
    // The owed snapshots are still being stored; the teacher starts a burst in the next step.
    await elapse(10);
    editing.updateItemChoiceBody("item_001", second!.choice_id, typed("C"), false);

    // Only the two owed states may exist before the typing pause.
    await elapse(190);
    expect(server.state.steps).toHaveLength(2);

    // The same burst continues 190 ms later, still before any 900 ms pause.
    editing.updateItemChoiceBody("item_001", second!.choice_id, typed("CD"), false);

    await elapse(5000);

    // Typing "B", the added step, then the "CD" burst.
    expect(server.state.steps).toHaveLength(3);
    expect(editing.history.pending.value).toBe(false);

    await editing.history.undo();
    await elapse(500);

    const choices = editing.workspaceDocument.value!.items[0]!.choices;
    expect(choiceText(choices[0]!)).toBe("B");
    expect(choiceText(choices[1]!)).toBe("");
  });
});
