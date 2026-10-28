/**
 * Exam workspace structure, moving an ordering question into a part
 * (TASK-SKRIPT-39-06-11 D1, D2).
 *
 * Expected behavior:
 *   Moving an ordering question into a part sends one move command. The
 *   document the server returns is installed as it is, with the question
 *   inside the part at the 1 point the server wrote, and the move stores one
 *   history step, so one undo returns the pre-move document. The client
 *   computes no points itself.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { exam, openEditing, response, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const structureApi = vi.hoisted(() => ({ moveExamWorkspaceItem: vi.fn() }));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  moveExamWorkspaceItem: structureApi.moveExamWorkspaceItem,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(structureApi), ...Object.values(toast)]) {
    fn.mockReset();
  }
});

afterEach(stopScopes);

const ORDERING_ID = "item_002";
const PART_ID = "parent_001";

/** A part holding one free-text child, and a standalone ordering question worth 3. */
function baselineDocument(): NativeExamDocument {
  const document = exam("Original", 2);
  document.items[0] = newTeacherItem("item_001", 1, "free_text");
  document.items[1] = { ...newTeacherItem(ORDERING_ID, 2, "ordering"), points: 3 };
  document.parents = [{ instruction: [], item_ids: ["item_001"], parent_id: PART_ID, place: 1 }];
  return document;
}

/** The server's answer: the ordering question now sits in the part, worth the 1 point it wrote. */
function movedDocument(document: NativeExamDocument): NativeExamDocument {
  return {
    ...document,
    items: document.items.map((item) =>
      item.item_id === ORDERING_ID ? { ...item, points: 1 } : item,
    ),
    parents: [{ ...document.parents[0]!, item_ids: ["item_001", ORDERING_ID] }],
  };
}

describe("moving an ordering question into a part", () => {
  it("installs the returned document and undoes the move in one step", async () => {
    const before = baselineDocument();
    const after = movedDocument(before);
    const { editing, server } = await openEditing(api, before);
    structureApi.moveExamWorkspaceItem.mockImplementation(async () => {
      const stepId = "step-move-1";
      server.documents.set(stepId, after);
      server.state.steps = [...server.state.steps, stepId];
      server.state.cursor = stepId;
      server.state.position = stepId;
      return response(after, stepId);
    });

    await editing.structure.moveItem(ORDERING_ID, PART_ID);
    await flushPromises();

    const command = structureApi.moveExamWorkspaceItem.mock.calls[0]!;
    expect(command.slice(0, 3)).toEqual([before.document_id, ORDERING_ID, PART_ID]);
    expect(server.state.steps).toEqual(["step-move-1"]);

    const installed = editing.workspaceDocument.value!;
    expect(installed.parents[0]!.item_ids).toEqual(["item_001", ORDERING_ID]);
    expect(installed.items.find((item) => item.item_id === ORDERING_ID)!.points).toBe(1);

    await editing.history.undo();
    await flushPromises();

    expect(server.state.steps).toEqual(["step-move-1"]);
    expect(editing.workspaceDocument.value!.parents[0]!.item_ids).toEqual(["item_001"]);
    expect(editing.workspaceDocument.value!.items.find((item) => item.item_id === ORDERING_ID)!.points).toBe(3);
  });
});
