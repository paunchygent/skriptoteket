import { describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  createDraft,
  createWorkspaceResponse,
  mockWorkspaceLoad,
  seedWorkspace,
  setupClassroomStateTests,
} from "./useClassroomState.specSupport";
import { useClassroomState } from "./useClassroomState";

describe("useClassroomState history", () => {
  setupClassroomStateTests();

  it("hydrates undo and redo availability from the backend workspace contract", async () => {
    const state = useClassroomState();
    mockWorkspaceLoad(
      createWorkspaceResponse("template-1", "grouping", {
        can_undo: true,
        can_redo: false,
      }),
    );

    await state.loadWorkspace("draft-1");

    expect(state.historyStatus).toEqual({
      can_undo: true,
      can_redo: false,
    });
    expect(state.canUndo).toBe(true);
    expect(state.canRedo).toBe(false);
  });

  it("flushes pending grouping autosave before undoing", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");
    clientMocks.apiPatch.mockResolvedValue(
      createWorkspaceResponse("template-1", "grouping", {
        can_undo: true,
        can_redo: false,
      }),
    );
    clientMocks.apiPost.mockResolvedValue(
      createWorkspaceResponse("template-1", "grouping", {
        can_undo: false,
        can_redo: true,
      }),
    );

    state.renameGroup("group-a", "Handledargrupp");
    expect(state.canUndo).toBe(true);
    await state.undoGroupingDraft();

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/undo",
    );
    expect(clientMocks.apiPatch.mock.invocationCallOrder[0]).toBeLessThan(
      clientMocks.apiPost.mock.invocationCallOrder[0],
    );
    expect(state.canUndo).toBe(false);
    expect(state.canRedo).toBe(true);
  });

  it("refreshes backend history availability after autosave completes", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");
    clientMocks.apiPatch.mockResolvedValue(
      createWorkspaceResponse("template-1", "grouping", {
        can_undo: true,
        can_redo: false,
      }),
    );
    clientMocks.apiPatch.mockClear();

    state.renameGroup("group-a", "Handledargrupp");
    expect(state.canUndo).toBe(true);

    await vi.advanceTimersByTimeAsync(900);

    const draftPatchCalls = clientMocks.apiPatch.mock.calls.filter(
      ([url]) => url === "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1",
    );
    const smartRulePatchCalls = clientMocks.apiPatch.mock.calls.filter(
      ([url]) => url === "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
    );

    expect(draftPatchCalls).toHaveLength(1);
    expect(smartRulePatchCalls).toHaveLength(0);
    expect(draftPatchCalls[0]?.[1]).toEqual(
      expect.objectContaining({
        expected_revision: 4,
        groups: expect.arrayContaining([
          expect.objectContaining({
            id: "group-a",
            name: "Handledargrupp",
          }),
        ]),
      }),
    );
    expect(state.draftPersistenceStatus).toBe("saved");
    expect(state.hasPendingAutosave).toBe(false);
    expect(state.historyStatus).toEqual({
      can_undo: true,
      can_redo: false,
    });
    expect(state.canUndo).toBe(true);
  });

  it("hydrates seating undo and redo availability from the backend workspace contract", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.historyStatus = {
      can_undo: true,
      can_redo: true,
    };

    expect(state.canUndo).toBe(true);
    expect(state.canRedo).toBe(true);
  });

  it("flushes pending seating autosave before undoing", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    clientMocks.apiPatch.mockResolvedValue(
      createWorkspaceResponse("template-1", "seating", {
        can_undo: true,
        can_redo: false,
      }),
    );
    clientMocks.apiPost.mockResolvedValue(
      createWorkspaceResponse("template-1", "seating", {
        can_undo: false,
        can_redo: true,
      }),
    );

    state.assignStudentToSeat("s1", "seat-1");
    expect(state.canUndo).toBe(true);
    await state.undoSeatingDraft();

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/undo",
    );
    expect(clientMocks.apiPatch.mock.invocationCallOrder[0]).toBeLessThan(
      clientMocks.apiPost.mock.invocationCallOrder[0],
    );
    expect(state.canUndo).toBe(false);
    expect(state.canRedo).toBe(true);
  });

  it("replays backend history state after redoing a seating step", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    clientMocks.apiPost.mockResolvedValue(
      createWorkspaceResponse("template-1", "seating", {
        can_undo: true,
        can_redo: false,
      }),
    );

    await state.redoSeatingDraft();

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/redo",
    );
    expect(state.canUndo).toBe(true);
    expect(state.canRedo).toBe(false);
  });

  it("does not run history actions without an active draft", async () => {
    const state = useClassroomState();

    await state.undoGroupingDraft();
    await state.redoSeatingDraft();

    expect(clientMocks.apiPost).not.toHaveBeenCalled();
  });

  it("rehydrates backend history state after redoing a grouping step", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");
    clientMocks.apiPost.mockResolvedValue(
      createWorkspaceResponse("template-1", "grouping", {
        can_undo: true,
        can_redo: false,
      }),
    );

    await state.redoGroupingDraft();

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/redo",
    );
    expect(state.canUndo).toBe(true);
    expect(state.canRedo).toBe(false);
  });

  it("ignores stale local group renames while undo is already in flight", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");
    let resolvePatch!: (value: ReturnType<typeof createWorkspaceResponse>) => void;
    let resolveUndo!: (value: ReturnType<typeof createWorkspaceResponse>) => void;
    clientMocks.apiPatch.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePatch = resolve;
        }),
    );
    clientMocks.apiPost.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveUndo = resolve;
        }),
    );

    state.renameGroup("group-a", "Handledargrupp");
    const undoPromise = state.undoGroupingDraft();

    await Promise.resolve();
    expect(resolvePatch).toBeTypeOf("function");
    resolvePatch({
      ...createWorkspaceResponse("template-1", "grouping", {
        can_undo: true,
        can_redo: false,
      }),
      draft: {
        ...createDraft("template-1", "grouping"),
        revision: 5,
      },
      groups: [
        { id: "group-a", name: "Handledargrupp", sort_order: 0, name_is_custom: true },
        { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
      ],
    });
    while (clientMocks.apiPost.mock.calls.length === 0) {
      await Promise.resolve();
    }

    state.renameGroup("group-a", "Sent namn");

    expect(state.groups[0]?.name).toBe("Handledargrupp");
    expect(resolveUndo).toBeTypeOf("function");
    resolveUndo(
      createWorkspaceResponse("template-1", "grouping", {
        can_undo: false,
        can_redo: true,
      }),
    );
    await undoPromise;
    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(state.groups[0]?.name).toBe("Grupp 1");
    expect(state.hasPendingAutosave).toBe(false);
    expect(state.canRedo).toBe(true);
  });
});
