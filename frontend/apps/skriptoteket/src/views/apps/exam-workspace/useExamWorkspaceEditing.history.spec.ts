/**
 * Exam workspace editing session: undo history across failed prerequisite
 * stores and edits while a replacing read runs.
 *
 * Expected behavior:
 *   - When the pending edit cannot be stored, a replacing command (Byt
 *     frågetyp) and undo do not run, and the pending edit stays.
 *   - While undo moves the position, editing and structure commands are
 *     refused, so nothing typed meanwhile is lost when the step arrives.
 *   - Storing a pending edit is the save: Ctrl/Cmd+S and exports flush the
 *     history, and the confirmed snapshot is the saved baseline.
 *   - The exam's only question cannot be deleted; the refusal is inline.
 *
 * Transport is a named double of the server's step store; the composables
 * are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import {
  conflict,
  exam,
  LINEAGE,
  openEditing,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";

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

describe("a failed prerequisite store (F2)", () => {
  it("does not run Byt frågetyp and keeps the pending edit", async () => {
    const { editing } = await openEditing(api);
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Lärarens osparade text");

    await editing.structure.changeType("item_001", "single_choice");

    expect(api.changeExamWorkspaceItemType).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens osparade text");
    expect(editing.workspaceDocument.value!.items[0]!.kind).toBe("free_text");
    expect(toast.failure).toHaveBeenCalledOnce();
  });

  it("does not undo past a pending edit it could not store", async () => {
    const { editing } = await openEditing(api);
    editing.setCourse(null);
    await flushPromises();
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    editing.setTitle("Lärarens osparade text");

    await editing.history.undo();

    expect(api.moveExamWorkspaceHistoryPosition).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens osparade text");
  });
});

describe("conflict recovery under the replacing lock", () => {
  it("reloads the exam when a server command meets a newer cursor", async () => {
    const { editing } = await openEditing(api);
    api.changeExamWorkspaceItemType.mockRejectedValueOnce(conflict());
    api.getExamWorkspaceDocument.mockResolvedValueOnce(response(exam("Från en annan flik"), "other-tab"));

    await editing.structure.changeType("item_001", "single_choice");

    expect(api.getExamWorkspaceDocument).toHaveBeenCalledOnce();
    expect(editing.workspaceDocument.value!.title).toBe("Från en annan flik");
  });

  it("reloads the exam when undo's store of the pending edit meets a newer cursor", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Ett");
    await editing.history.flush();
    server.state.cursor = "other-tab";
    api.getExamWorkspaceDocument.mockResolvedValueOnce(response(exam("Från en annan flik"), "other-tab"));
    editing.setTitle("Osparad");

    await editing.history.undo();
    await flushPromises();

    expect(api.getExamWorkspaceDocument).toHaveBeenCalledOnce();
    expect(api.moveExamWorkspaceHistoryPosition).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Från en annan flik");
    // The decided 409 policy: the reload replaces the pending edit.
    expect(editing.history.pending.value).toBe(false);

    // The reloaded history still navigates: the next undo moves to its earlier step.
    await editing.history.undo();
    expect(api.moveExamWorkspaceHistoryPosition).toHaveBeenCalledTimes(1);
    expect(editing.workspaceDocument.value!.title).toBe("Original");
  });
});

describe("the edit lease on a 409 (K8)", () => {
  function leaseHeld(): ApiError {
    return new ApiError({
      code: "EDIT_LEASE_HELD",
      message: "Provet redigeras i en annan flik.",
      status: 409,
    });
  }

  it("turns read-only on a lease-held undo store and keeps the pending edit", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Ett");
    await editing.history.flush();
    server.state.cursor = "other-tab";
    editing.setTitle("Osparad");
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
    api.getExamWorkspaceDocument.mockClear();

    await editing.history.undo();
    await flushPromises();

    expect(api.moveExamWorkspaceHistoryPosition).not.toHaveBeenCalled();
    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Osparad");
    expect(editing.history.pending.value).toBe(true);
    expect(editing.leaseReadOnly.value).toBe(true);
    expect(toast.failure).not.toHaveBeenCalled();
  });

  it("turns read-only on a lease-held server command without discarding the edit", async () => {
    const { editing } = await openEditing(api);
    editing.setTitle("Lärarens osparade text");
    await editing.history.flush();
    api.changeExamWorkspaceItemType.mockRejectedValueOnce(leaseHeld());
    api.getExamWorkspaceDocument.mockClear();

    await editing.structure.changeType("item_001", "single_choice");

    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens osparade text");
    expect(editing.leaseReadOnly.value).toBe(true);
  });

  it("waits for a running operation on a busy-time 409 instead of skipping the reload", async () => {
    const { editing } = await openEditing(api);
    let releaseOpen!: (value: unknown) => void;
    api.getExamWorkspaceDocument.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          releaseOpen = resolve;
        }),
    );
    const token = await editing.noteRouteRequest();
    if (token === null) {
      throw new Error("expected the route request to settle");
    }
    const opening = editing.openDocument(LINEAGE, token);
    await flushPromises();
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);

    api.getExamWorkspaceDocument.mockImplementationOnce(async () =>
      response(exam("Från en annan flik"), "other-tab"),
    );
    const reloading = editing.reloadDocument();
    await flushPromises();
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);

    releaseOpen(response(exam("Opened"), "cursor-open"));
    await opening;
    await reloading;
    // The stale reload hands over to the gate, whose fresh read installs after.
    await flushPromises();
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(editing.workspaceDocument.value!.title).toBe("Från en annan flik");
  });
});

describe("editing while undo moves the position (F4)", () => {
  it("refuses edits and commands until the replacing step has arrived", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Steg ett");
    await editing.history.flush();
    let release!: () => void;
    api.moveExamWorkspaceHistoryPosition.mockImplementationOnce(
      (_l: string, request: { expectedCursor: string; stepId: string }) =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              document: server.documents.get(request.stepId)!,
              export_blockers: [],
              history: {
                baseline_step_id: "step-0",
                cursor: server.state.cursor,
                position_step_id: request.stepId,
                step_ids: [...server.state.steps],
              },
            });
        }),
    );

    const moving = editing.history.undo();
    await flushPromises();
    expect(api.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    expect(editing.isBusy.value).toBe(true);
    editing.setTitle("Skrivet medan ångra laddade");
    await editing.structure.changeType("item_001", "single_choice");
    expect(editing.workspaceDocument.value!.title).toBe("Steg ett");
    expect(api.changeExamWorkspaceItemType).not.toHaveBeenCalled();

    release();
    await moving;
    expect(editing.workspaceDocument.value!.title).toBe("Original");
    expect(editing.isBusy.value).toBe(false);
    editing.setTitle("Efter ångra");
    expect(editing.workspaceDocument.value!.title).toBe("Efter ångra");
  });
});

describe("deleting the only question (F3)", () => {
  it("is refused inline and leaves the exam and its history intact", async () => {
    const { editing } = await openEditing(api, exam("Original", 1));

    editing.structure.deleteItem("item_001");
    await flushPromises();

    expect(editing.workspaceDocument.value!.items).toHaveLength(1);
    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(editing.structure.deleteNotice.value).toEqual({
      kind: "refused",
      text: "Provet måste ha minst en fråga.",
    });
    expect(toast.failure).not.toHaveBeenCalled();
  });
});
