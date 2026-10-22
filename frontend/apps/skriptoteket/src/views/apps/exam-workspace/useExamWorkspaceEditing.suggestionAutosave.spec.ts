/**
 * Exam workspace editing session: an arriving AI suggestion schedules its own
 * store (walk repair D1, TASK-SKRIPT-41-01-03).
 *
 * Expected behavior:
 *   A facit suggestion that changes the open copy is stored like typing after
 *   the 900 ms pause, with no further teacher edit: the header leaves
 *   "Sparar …" for the saved state and the server holds the suggestion. A
 *   suggestion that changes nothing, and one requested for another exam
 *   opening, schedule no store. An arrival a save read without runs again on
 *   its response, and that replay schedules the store which keeps it. A gap's
 *   automatic misspellings that arrive after the teacher's edit was stored
 *   are stored the same way.
 *   Transport is the named double of the server's step store; the composables
 *   are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeAnswerKeySuggestion } from "../../../api/examWorkspace";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import { deferred } from "./useExamWorkspaceDocument.specSupport";
import {
  exam,
  LINEAGE,
  openEditing,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";
import { EXAM_WORKSPACE_TYPING_PAUSE_MS } from "./useExamWorkspaceHistory";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
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

type Editing = Awaited<ReturnType<typeof openEditing>>["editing"];

const PAST_PAUSE_MS = EXAM_WORKSPACE_TYPING_PAUSE_MS + 100;

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
  vi.useFakeTimers();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

async function elapse(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

/** A facit suggestion for the free-text question the editing fixture opens. */
function facitSuggestion(): NativeAnswerKeySuggestion {
  return {
    correct_choice_ids: [],
    fingerprint: "a".repeat(64),
    gap_accepted_values: [],
    match_pairs: [],
    model: "model",
    prompt_template_version: "v1",
    provider_profile_id: "profile",
  };
}

function openingOf(editing: Editing): ExamWorkspaceOpening {
  const opening = editing.openExam.value;
  if (!opening) {
    throw new Error("expected an open exam");
  }
  return opening;
}

function deliver(
  editing: Editing,
  opening: ExamWorkspaceOpening,
  suggestion: NativeAnswerKeySuggestion,
): void {
  editing.applyArrivingSuggestions(opening, [{ item_id: "item_001", suggestion }]);
}

describe("an arriving facit suggestion", () => {
  it("is stored after the typing pause with no further edit, ending in the saved state", async () => {
    const { editing } = await openEditing(api);
    const suggestion = facitSuggestion();

    deliver(editing, openingOf(editing), suggestion);

    expect(editing.workspaceDocument.value!.items[0]!.ai_suggestion).toEqual(suggestion);
    expect(editing.history.saveStatus.value.state).toBe("saving");
    await elapse(PAST_PAUSE_MS);

    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    const stored = api.storeExamWorkspaceUndoStep.mock.calls[0]![1].document;
    expect(stored.items[0].ai_suggestion).toEqual(suggestion);
    expect(editing.history.saveStatus.value.state).toBe("saved");
  });

  it("schedules no store when it changes nothing on the question", async () => {
    const suggestion = facitSuggestion();
    const baseline = exam("Original", 2);
    baseline.items[0] = { ...baseline.items[0]!, ai_suggestion: suggestion };
    const { editing } = await openEditing(api, baseline);

    deliver(editing, openingOf(editing), facitSuggestion());
    await elapse(PAST_PAUSE_MS);

    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(editing.history.saveStatus.value.state).toBe("saved");
  });

  it("schedules no store when its exam opening is not the open one", async () => {
    const { editing } = await openEditing(api);
    const before = editing.workspaceDocument.value;

    deliver(editing, { lineageId: LINEAGE }, facitSuggestion());
    await elapse(PAST_PAUSE_MS);

    expect(editing.workspaceDocument.value).toBe(before);
    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
  });
});

describe("an arrival another save read without", () => {
  it("is stored after its replay onto that save's response", async () => {
    const { editing } = await openEditing(api);
    editing.setTitle("Nytt");
    await elapse(PAST_PAUSE_MS);
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();

    const moving = deferred<void>();
    const movePosition = api.moveExamWorkspaceHistoryPosition.getMockImplementation()!;
    api.moveExamWorkspaceHistoryPosition.mockImplementation(async (...args: unknown[]) => {
      await moving.promise;
      return movePosition(...args);
    });
    const suggestion = facitSuggestion();

    // Ångra replaces the copy: the arrival lands during its read and runs
    // again on the step it installs.
    const undoing = editing.history.undo();
    await flushPromises();
    expect(api.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    deliver(editing, openingOf(editing), suggestion);
    moving.resolve();
    await undoing;
    await flushPromises();

    expect(editing.workspaceDocument.value!.items[0]!.ai_suggestion).toEqual(suggestion);
    // The replay rearms the pause; nothing is stored before it fires.
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    await elapse(PAST_PAUSE_MS);

    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    expect(editing.history.saveStatus.value.state).toBe("saved");
  });
});

describe("a gap's automatic misspellings", () => {
  it("are stored after the typing pause when they arrive after the edit was stored", async () => {
    const baseline = exam();
    baseline.items[0] = { ...gapItem("teacher_authored", [["gap_001", ["Stockholm"]]], null), points: 2 };
    const { editing } = await openEditing(api, baseline);
    let reply!: (automatic: string[]) => void;
    api.requestExamWorkspaceAnswerMisspellings.mockReturnValueOnce(
      new Promise((resolve) => {
        reply = (automatic) => resolve({ automatic_values: automatic });
      }),
    );

    editing.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    await editing.history.flush();
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    reply(["Götebprg"]);
    await flushPromises();
    expect(editing.workspaceDocument.value!.items[0]!.gaps[0]!.automatic_values).toEqual(["Götebprg"]);
    await elapse(PAST_PAUSE_MS);

    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    const stored = api.storeExamWorkspaceUndoStep.mock.calls[1]![1].document;
    expect(stored.items[0].gaps[0].automatic_values).toEqual(["Götebprg"]);
    expect(editing.history.saveStatus.value.state).toBe("saved");
  });
});
