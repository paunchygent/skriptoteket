/**
 * Exam workspace editing session: gap creation through `createItemGap`.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J6, ledger L5-L6):
 *   `createItemGap` writes one gap creation as one undoable structural edit:
 *   the body plus the new gap record together, never through
 *   `updateItemBody`. Undo removes exactly the last created gap (body and
 *   record), and redo restores it.
 *
 * Transport is the named double of the server's step store; the composables
 * are the production ones.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { withNewGap } from "./examWorkspaceGapEdits";
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

function gapExam(): NativeExamDocument {
  const baseline = exam("Original", 1);
  // A converted Lucktext already carrying its first gap: a new Lucktext
  // starts empty (L2), so the fixture grows the starting gap through the
  // production creation, keeping a valid teacher-authored key.
  baseline.items[0] = withNewGap(
    { ...newTeacherItem("item_001", 1, "gap_fill"), points: 2 },
    bodyWith(["gap_001"]),
    "gap_001",
    "ett",
  );
  return baseline;
}

/** One paragraph placing `gapIds` in order between words. */
function bodyWith(gapIds: string[]): NativeExamBodyParagraph[] {
  const segments: NativeExamBodySegment[] = [
    { kind: "text", marks: [], text: "Start " },
  ];
  for (const gapId of gapIds) {
    segments.push({ gap_id: gapId, kind: "gap" });
    segments.push({ kind: "text", marks: [], text: " mellan " });
  }
  return [{ heading_level: null, segments }];
}

function gapIdsOf(document: NativeExamDocument): string[] {
  return document.items[0]!.gaps.map((gap) => gap.gap_id);
}

describe("createItemGap through the editing session", () => {
  it("writes three gap creations as three undoable structural steps", async () => {
    const { editing, server } = await openEditing(api, gapExam());

    editing.createItemGap("item_001", bodyWith(["gap_001", "gap_002"]), "gap_002", "ord två");
    editing.createItemGap("item_001", bodyWith(["gap_001", "gap_002", "gap_003"]), "gap_003", "ord tre");
    editing.createItemGap(
      "item_001",
      bodyWith(["gap_001", "gap_002", "gap_003", "gap_004"]),
      "gap_004",
      "ord fyra",
    );
    await editing.history.flush();

    expect(server.state.steps).toHaveLength(3);
    const created = editing.workspaceDocument.value!;
    expect(gapIdsOf(created)).toEqual(["gap_001", "gap_002", "gap_003", "gap_004"]);
    expect(created.items[0]!.body).toEqual(bodyWith(["gap_001", "gap_002", "gap_003", "gap_004"]));
    expect(created.items[0]!.gaps[3]!.accepted_values).toEqual(["ord fyra"]);

    await editing.history.undo();
    const undoneOnce = editing.workspaceDocument.value!;
    expect(gapIdsOf(undoneOnce)).toEqual(["gap_001", "gap_002", "gap_003"]);
    expect(undoneOnce.items[0]!.body).toEqual(bodyWith(["gap_001", "gap_002", "gap_003"]));

    await editing.history.undo();
    const undoneTwice = editing.workspaceDocument.value!;
    expect(gapIdsOf(undoneTwice)).toEqual(["gap_001", "gap_002"]);
    expect(undoneTwice.items[0]!.body).toEqual(bodyWith(["gap_001", "gap_002"]));

    await editing.history.redo();
    const redone = editing.workspaceDocument.value!;
    expect(gapIdsOf(redone)).toEqual(["gap_001", "gap_002", "gap_003"]);
    expect(redone.items[0]!.body).toEqual(bodyWith(["gap_001", "gap_002", "gap_003"]));
    expect(redone.items[0]!.gaps[2]!.accepted_values).toEqual(["ord tre"]);
  });
});
