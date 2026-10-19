/**
 * Exam workspace editing session: undo across tool-made gaps and a refused save.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 repair A1):
 *   A word click or drag through `createItemGap` is one healthy undo step, and
 *   typing after it undoes step by step with redo returning. When a later gap
 *   leaves the key partial (`""` seed) the server refuses every store with a
 *   422, so Ångra once discards the refused working copy to the last stored
 *   step with nothing pending, and Ångra again removes the word-made gap. A
 *   transient store failure instead keeps the pending edit in front of the
 *   teacher.
 *
 * Transport is the named double of the server's step store; the composables
 * are the production ones. The 900 ms pause is advanced explicitly, never
 * awaited as a timing probe.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { withNewGap } from "./examWorkspaceGapEdits";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { EXAM_WORKSPACE_TYPING_PAUSE_MS } from "./useExamWorkspaceHistory";
import {
  exam,
  openEditing,
  refuseSaveRefusedDrafts,
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

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

/** A keyed Lucktext already carrying its first gap, as `createItemGap` keys it. */
function gapExam(): NativeExamDocument {
  const baseline = exam("Original", 1);
  baseline.items[0] = withNewGap(
    { ...newTeacherItem("item_001", 1, "gap_fill"), points: 2 },
    bodyWith(["gap_001"]),
    "gap_001",
    "ett",
  );
  return baseline;
}

/** One paragraph placing `gapIds` in order between words, starting with `lead`. */
function bodyWith(gapIds: string[], lead = "Start "): NativeExamBodyParagraph[] {
  const segments: NativeExamBodySegment[] = [{ kind: "text", marks: [], text: lead }];
  for (const gapId of gapIds) {
    segments.push({ gap_id: gapId, kind: "gap" });
    segments.push({ kind: "text", marks: [], text: " mellan " });
  }
  return [{ heading_level: null, segments }];
}

function gapIdsOf(document: NativeExamDocument): string[] {
  return document.items[0]!.gaps.map((gap) => gap.gap_id);
}

function leadOf(document: NativeExamDocument): string {
  const first = document.items[0]!.body[0]!.segments[0]!;
  if (first.kind !== "text") {
    throw new Error("expected the body to start with text");
  }
  return first.text;
}

/** Type into the question body: a non-structural edit stored after the pause. */
async function typeIntoBody(
  editing: Awaited<ReturnType<typeof openEditing>>["editing"],
  lead: string,
): Promise<void> {
  editing.updateItemBody(
    "item_001",
    bodyWith(gapIdsOf(editing.workspaceDocument.value!), lead),
    false,
  );
  vi.advanceTimersByTime(EXAM_WORKSPACE_TYPING_PAUSE_MS);
  await flushPromises();
}

async function openGapExam(): Promise<Awaited<ReturnType<typeof openEditing>>> {
  return openEditing(api, gapExam());
}

describe("tool-made gaps keep a healthy undo history", () => {
  it("a word-made gap and typing undo and redo step by step", async () => {
    const { editing } = await openGapExam();
    editing.createItemGap("item_001", bodyWith(["gap_001", "gap_002"]), "gap_002", "ord");
    await editing.history.flush();

    vi.useFakeTimers();
    await typeIntoBody(editing, "Start! ");
    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001", "gap_002"]);
    expect(leadOf(editing.workspaceDocument.value!)).toBe("Start! ");

    await editing.history.undo();
    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001", "gap_002"]);
    expect(leadOf(editing.workspaceDocument.value!)).toBe("Start ");
    expect(editing.workspaceDocument.value!.items[0]!.gaps[1]!.accepted_values).toEqual(["ord"]);

    await editing.history.undo();
    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001"]);
    expect(editing.workspaceDocument.value!.items[0]!.body).toEqual(bodyWith(["gap_001"]));

    await editing.history.redo();
    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001", "gap_002"]);
    await editing.history.redo();
    expect(leadOf(editing.workspaceDocument.value!)).toBe("Start! ");
  });

  it("a drag-made multi-word gap and typing undo and redo step by step", async () => {
    const { editing } = await openGapExam();
    editing.createItemGap("item_001", bodyWith(["gap_001", "gap_002"]), "gap_002", "ord två tre");
    await editing.history.flush();

    vi.useFakeTimers();
    await typeIntoBody(editing, "Start! ");

    await editing.history.undo();
    expect(editing.workspaceDocument.value!.items[0]!.gaps[1]!.accepted_values).toEqual(["ord två tre"]);
    expect(leadOf(editing.workspaceDocument.value!)).toBe("Start ");

    await editing.history.undo();
    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001"]);
    expect(editing.workspaceDocument.value!.items[0]!.body).toEqual(bodyWith(["gap_001"]));

    await editing.history.redo();
    await editing.history.redo();
    expect(leadOf(editing.workspaceDocument.value!)).toBe("Start! ");
    expect(editing.workspaceDocument.value!.items[0]!.gaps[1]!.accepted_values).toEqual(["ord två tre"]);
  });
});

describe("a gap the save rules refuse", () => {
  it("is discarded by the first undo, and the next undo removes the word-made gap", async () => {
    const { editing } = await openGapExam();
    refuseSaveRefusedDrafts(api);
    editing.createItemGap("item_001", bodyWith(["gap_001", "gap_002"]), "gap_002", "ord");
    await editing.history.flush();
    editing.createItemGap("item_001", bodyWith(["gap_001", "gap_002", "gap_003"]), "gap_003", "");
    await editing.history.flush();

    vi.useFakeTimers();
    await typeIntoBody(editing, "Start! ");
    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001", "gap_002", "gap_003"]);

    await editing.history.undo();

    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001", "gap_002"]);
    expect(leadOf(editing.workspaceDocument.value!)).toBe("Start ");
    expect(editing.history.pending.value).toBe(false);
    expect(editing.history.canRedo.value).toBe(false);
    expect(toast.failure).not.toHaveBeenCalled();

    await editing.history.undo();

    expect(gapIdsOf(editing.workspaceDocument.value!)).toEqual(["gap_001"]);
    expect(editing.workspaceDocument.value!.items[0]!.body).toEqual(bodyWith(["gap_001"]));
  });
});

describe("a transient store failure", () => {
  it("keeps the pending edit in front of the teacher after undo", async () => {
    const { editing } = await openGapExam();
    editing.createItemGap("item_001", bodyWith(["gap_001", "gap_002"]), "gap_002", "ord");
    await editing.history.flush();
    api.storeExamWorkspaceUndoStep.mockRejectedValue(
      new ApiError({
        code: "UPSTREAM_ERROR",
        message: "Upstream error",
        details: [],
        correlationId: null,
        status: 500,
      }),
    );

    vi.useFakeTimers();
    await typeIntoBody(editing, "Start! ");

    await editing.history.undo();

    expect(leadOf(editing.workspaceDocument.value!)).toBe("Start! ");
    expect(editing.history.pending.value).toBe(true);
    expect(api.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
  });
});
