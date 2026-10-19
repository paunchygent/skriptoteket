/**
 * Exam workspace selection: empty gaps are removed when the teacher leaves the question.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviour 10, U4 rule 3, L3):
 *   When the teacher leaves a question with an answer key — selects another
 *   question, closes the editor for an instruction, or leaves the workspace
 *   route — every empty gap in it is removed silently as one structural undo
 *   step, with no toast. Ångra brings the gaps back. A question without an
 *   answer key loses nothing, and reselecting the same question removes
 *   nothing. The removal is an ordinary `updateItemBody` edit, so it autosaves
 *   like every step. It never runs on page unload: no unload handler is
 *   mounted, and scope disposal only runs for in-SPA unmounts.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { placedGapIds } from "./examWorkspaceRichTextDocument";
import { useExamWorkspaceSelection, EXAM_INSTRUCTIONS_ENTRY_ID } from "./useExamWorkspaceSelection";
import {
  exam,
  openEditing,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
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

afterEach(() => {
  while (selectionScopes.length > 0) {
    selectionScopes.pop()?.stop();
  }
  stopScopes();
  document.body.innerHTML = "";
});

async function settle(): Promise<void> {
  await nextTick();
  await nextTick();
  await flushPromises();
}

/** Two keyed Lucktext questions: item_001 carries the empty gap_002, item_002 is fully answered. */
function twoQuestionExam(): NativeExamDocument {
  const baseline = exam("Prov", 2);
  baseline.items[0] = buildGapItem();
  baseline.items[1] = buildGapItem({
    item_id: "item_002",
    gaps: [buildGap("gap_001", ["100"]), buildGap("gap_002", ["noll"])],
    sequence: 2,
  });
  return baseline;
}

function itemOf(editing: { workspaceDocument: { value: NativeExamDocument | null } }, itemId: string): NativeExamItem {
  const found = editing.workspaceDocument.value?.items.find((item) => item.item_id === itemId);
  if (!found) {
    throw new Error(`no item ${itemId}`);
  }
  return found;
}

describe("useExamWorkspaceSelection empty gap cleanup", () => {
  it("removes every empty gap as one structural step when another question is selected", async () => {
    const { editing, server } = await openEditing(api, twoQuestionExam());
    const selection = inScopeFor(() => useExamWorkspaceSelection({
      editing,
      importOpen: ref(false),
      listOpen: ref(false),
      afterGoto: () => undefined,
    }));
    const updated = vi.spyOn(editing, "updateItemBody");

    selection.selectEntry("item_002");
    await settle();

    expect(updated).toHaveBeenCalledTimes(1);
    expect(updated).toHaveBeenCalledWith("item_001", expect.anything(), true);
    const cleaned = itemOf(editing, "item_001");
    expect(cleaned.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
    expect(placedGapIds(cleaned.body)).toEqual(["gap_001"]);
    // The other question is untouched.
    expect(itemOf(editing, "item_002").gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    expect(server.state.steps).toHaveLength(1);
    expect(toast.failure).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("removes empty gaps when the editor closes for the exam instruction", async () => {
    const { editing } = await openEditing(api, twoQuestionExam());
    const selection = inScopeFor(() => useExamWorkspaceSelection({
      editing,
      importOpen: ref(false),
      listOpen: ref(false),
      afterGoto: () => undefined,
    }));
    const updated = vi.spyOn(editing, "updateItemBody");

    selection.selectEntry(EXAM_INSTRUCTIONS_ENTRY_ID);
    await settle();

    expect(updated).toHaveBeenCalledTimes(1);
    expect(itemOf(editing, "item_001").gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
    expect(toast.failure).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("removes empty gaps when the workspace route is left", async () => {
    const { editing, server } = await openEditing(api, twoQuestionExam());
    const scope = effectScope();
    const selection = scope.run(() => useExamWorkspaceSelection({
      editing,
      importOpen: ref(false),
      listOpen: ref(false),
      afterGoto: () => undefined,
    }))!;
    const updated = vi.spyOn(editing, "updateItemBody");
    void selection;

    scope.stop();
    await settle();

    expect(updated).toHaveBeenCalledTimes(1);
    expect(itemOf(editing, "item_001").gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
    expect(server.state.steps).toHaveLength(1);
    expect(toast.failure).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("keeps every gap of a question without an answer key", async () => {
    const baseline = twoQuestionExam();
    baseline.items[0] = buildGapItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    });
    const { editing } = await openEditing(api, baseline);
    const selection = inScopeFor(() => useExamWorkspaceSelection({
      editing,
      importOpen: ref(false),
      listOpen: ref(false),
      afterGoto: () => undefined,
    }));
    const updated = vi.spyOn(editing, "updateItemBody");

    selection.selectEntry("item_002");
    await settle();

    expect(updated).not.toHaveBeenCalled();
    expect(itemOf(editing, "item_001").gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
  });

  it("removes nothing when the same question is selected again", async () => {
    const { editing } = await openEditing(api, twoQuestionExam());
    const selection = inScopeFor(() => useExamWorkspaceSelection({
      editing,
      importOpen: ref(false),
      listOpen: ref(false),
      afterGoto: () => undefined,
    }));
    const updated = vi.spyOn(editing, "updateItemBody");

    selection.selectEntry("item_001");
    await settle();

    expect(updated).not.toHaveBeenCalled();
    expect(itemOf(editing, "item_001").gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
  });

  it("stores the cleanup as one step that Ångra brings back", async () => {
    const { editing, server } = await openEditing(api, twoQuestionExam());
    api.moveExamWorkspaceHistoryPosition.mockImplementation(
      async (_lineage: string, request: { expectedCursor: string; stepId: string }) => {
        const position = request.stepId;
        server.state.position = position;
        server.state.cursor = `move-${position}`;
        return {
          document: server.documents.get(position)!,
          export_blockers: [],
          history: {
            baseline_step_id: "step-0",
            cursor: server.state.cursor,
            position_step_id: server.state.position,
            step_ids: [...server.state.steps],
          },
        };
      },
    );
    const selection = inScopeFor(() => useExamWorkspaceSelection({
      editing,
      importOpen: ref(false),
      listOpen: ref(false),
      afterGoto: () => undefined,
    }));

    selection.selectEntry("item_002");
    await settle();
    await flushPromises();

    expect(itemOf(editing, "item_001").gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
    expect(server.state.steps).toHaveLength(1);

    await editing.history.undo();
    await settle();
    await flushPromises();

    const restored = itemOf(editing, "item_001");
    expect(restored.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    expect(placedGapIds(restored.body)).toEqual(["gap_001", "gap_002"]);
    expect(toast.failure).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("mounts no page-unload handler", async () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const { editing } = await openEditing(api, twoQuestionExam());
    inScopeFor(() => useExamWorkspaceSelection({
      editing,
      importOpen: ref(false),
      listOpen: ref(false),
      afterGoto: () => undefined,
    }));

    expect(addSpy.mock.calls.some(([event]) => event === "beforeunload")).toBe(false);
    addSpy.mockRestore();
  });
});

const selectionScopes: ReturnType<typeof effectScope>[] = [];

/** Run the selection in its own scope so route-leave tests can stop only it. */
function inScopeFor<T>(run: () => T): T {
  const scope = effectScope();
  selectionScopes.push(scope);
  const result = scope.run(run);
  if (result === undefined) {
    throw new Error("the selection scope did not run");
  }
  return result;
}
