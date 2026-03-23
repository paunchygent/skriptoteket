import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useClassroomState } from "./useClassroomState";

const clientMocks = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  isApiError: vi.fn(() => false),
}));

vi.mock("../../api/client", () => {
  class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  }

  return {
    ApiError,
    apiDelete: clientMocks.apiDelete,
    apiGet: clientMocks.apiGet,
    apiPatch: clientMocks.apiPatch,
    apiPost: clientMocks.apiPost,
    isApiError: clientMocks.isApiError,
  };
});

function createDraft(
  templateId: string | null = "template-1",
  draftKind: "seating" | "grouping" = "seating",
) {
  return {
    id: "draft-1",
    roster_id: "roster-1",
    draft_kind: draftKind,
    template_id: templateId,
    status: "active" as const,
    revision: 4,
    last_opened_at: "2026-03-21T10:00:00Z",
  };
}

function createWorkspaceResponse(
  templateId: string | null = "template-1",
  draftKind: "seating" | "grouping" = "seating",
  historyStatus: { can_undo: boolean; can_redo: boolean } = {
    can_undo: false,
    can_redo: false,
  },
) {
  return {
    draft: createDraft(templateId, draftKind),
    roster: {
      id: "roster-1",
      name: "Klass 9A",
      students: [
        { id: "s1", display_name: "Student 1" },
        { id: "s2", display_name: "Student 2" },
        { id: "s3", display_name: "Student 3" },
      ],
    },
    template:
      templateId === null
        ? null
        : {
            id: "template-1",
            name: "Sal 101",
            seats: [
              { id: "seat-1", x: 0, y: 0, zone: "front" },
              { id: "seat-2", x: 120, y: 0, zone: "front" },
            ],
            fixtures: [],
          },
    groups: [
      { id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false },
      { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ],
    group_assignments: [],
    seat_assignments: [],
    student_planning_meta: [],
    history_status: historyStatus,
  };
}

function seedWorkspace() {
  const state = useClassroomState();
  state.roster = {
    id: "roster-1",
    name: "Klass 9A",
    students: [
      { id: "s1", display_name: "Student 1" },
      { id: "s2", display_name: "Student 2" },
      { id: "s3", display_name: "Student 3" },
    ],
  };
  state.template = {
    id: "template-1",
    name: "Sal 101",
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: "front" },
      { id: "seat-2", x: 120, y: 0, zone: "front" },
    ],
    fixtures: [],
  };
  state.groups = [
    { id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false },
    { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
  ];
  state.groupAssignmentsByStudentId = {};
  state.seatAssignmentsByStudentId = {};
  state.studentPlanningMetaByStudentId = {};
  return state;
}

describe("useClassroomState", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    clientMocks.apiGet.mockReset();
    clientMocks.apiPatch.mockReset();
    clientMocks.apiPost.mockReset();
    clientMocks.apiDelete.mockReset();
    clientMocks.isApiError.mockReset();
    clientMocks.isApiError.mockReturnValue(false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("assigns and removes students from groups", () => {
    const state = seedWorkspace();

    state.assignStudentToGroup("s1", "group-a");

    expect(state.groupAssignmentsByStudentId["s1"]).toBe("group-a");
    expect(state.studentsByGroupId["group-a"]).toHaveLength(1);

    state.removeStudentFromGroup("s1");

    expect(state.groupAssignmentsByStudentId["s1"]).toBeNull();
    expect(state.ungroupedStudents).toHaveLength(3);
  });

  it("reassigns occupied seats to the latest student", () => {
    const state = seedWorkspace();

    state.assignStudentToSeat("s1", "seat-1");
    state.assignStudentToSeat("s2", "seat-1");

    expect(state.seatAssignmentsByStudentId["s1"]).toBeNull();
    expect(state.seatAssignmentsByStudentId["s2"]).toBe("seat-1");
  });

  it("supports group lifecycle operations", () => {
    const state = seedWorkspace();

    state.addGroup("Grupp C");
    const createdGroup = state.groups.find((group) => group.name === "Grupp C");

    expect(createdGroup).toBeTruthy();

    state.moveGroup(createdGroup!.id, -1);
    state.renameGroup(createdGroup!.id, "Nya Grupp C");

    expect(state.groups.map((group) => `${group.sort_order}:${group.name}`)).toEqual([
      "0:Grupp 1",
      "1:Nya Grupp C",
      "2:Grupp 3",
    ]);

    expect(state.groups.find((group) => group.id === createdGroup!.id)?.name).toBe("Nya Grupp C");

    state.removeGroup(createdGroup!.id);

    expect(state.groups.find((group) => group.id === createdGroup!.id)).toBeUndefined();
  });

  it("keeps group ordering meaningful when moving cards up and down", () => {
    const state = seedWorkspace();

    state.addGroup("Grupp C");
    const createdGroup = state.groups.find((group) => group.name === "Grupp C");

    expect(createdGroup).toBeTruthy();

    state.moveGroup(createdGroup!.id, -1);
    state.moveGroup("group-a", 1);

    expect(state.groups.map((group) => ({
      id: group.id,
      sort_order: group.sort_order,
    }))).toEqual([
      { id: createdGroup!.id, sort_order: 0 },
      { id: "group-a", sort_order: 1 },
      { id: "group-b", sort_order: 2 },
    ]);
  });

  it("renumbers default group names when groups are reordered or removed", () => {
    const state = seedWorkspace();

    state.addGroup();
    const createdGroup = state.groups.find((group) => group.sort_order === 2);

    expect(createdGroup).toBeTruthy();
    expect(createdGroup?.name).toBe("Grupp 3");
    expect(createdGroup?.name_is_custom).toBe(false);

    state.moveGroup(createdGroup!.id, -1);

    expect(state.groups.map((group) => ({
      id: group.id,
      name: group.name,
      sort_order: group.sort_order,
    }))).toEqual([
      { id: "group-a", name: "Grupp 1", sort_order: 0 },
      { id: createdGroup!.id, name: "Grupp 2", sort_order: 1 },
      { id: "group-b", name: "Grupp 3", sort_order: 2 },
    ]);

    state.removeGroup("group-a");

    expect(state.groups.map((group) => ({
      id: group.id,
      name: group.name,
      sort_order: group.sort_order,
    }))).toEqual([
      { id: createdGroup!.id, name: "Grupp 1", sort_order: 0 },
      { id: "group-b", name: "Grupp 2", sort_order: 1 },
    ]);
  });

  it("preserves custom group names while default groups continue to renumber", () => {
    const state = seedWorkspace();

    state.renameGroup("group-b", "Handledargrupp");
    state.moveGroup("group-b", -1);

    expect(state.groups.map((group) => ({
      id: group.id,
      name: group.name,
      sort_order: group.sort_order,
      name_is_custom: group.name_is_custom,
    }))).toEqual([
      { id: "group-b", name: "Handledargrupp", sort_order: 0, name_is_custom: true },
      { id: "group-a", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ]);
  });

  it("treats an explicit default label as system-managed naming", () => {
    const state = seedWorkspace();

    state.renameGroup("group-b", "Handledargrupp");
    state.renameGroup("group-b", "Grupp 2");
    state.moveGroup("group-b", -1);

    expect(state.groups.map((group) => ({
      id: group.id,
      name: group.name,
      sort_order: group.sort_order,
      name_is_custom: group.name_is_custom,
    }))).toEqual([
      { id: "group-b", name: "Grupp 1", sort_order: 0, name_is_custom: false },
      { id: "group-a", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ]);
  });

  it("does not mark the workspace dirty when a group rename is a no-op", () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");

    state.renameGroup("group-a", "Grupp 1");

    expect(state.hasPendingAutosave).toBe(false);
    expect(state.saveStatus).toBe("idle");
  });

  it("randomizes groups without changing group count or names", () => {
    const state = seedWorkspace();
    const randomSpy = vi.spyOn(Math, "random");
    randomSpy
      .mockReturnValueOnce(0.85)
      .mockReturnValueOnce(0.1)
      .mockReturnValueOnce(0.6)
      .mockReturnValueOnce(0.2);

    state.renameGroup("group-a", "Handledargrupp");
    state.renameGroup("group-b", "Fördjupning");
    state.randomizeGroups();

    expect(state.groups).toEqual([
      expect.objectContaining({ id: "group-a", name: "Handledargrupp" }),
      expect.objectContaining({ id: "group-b", name: "Fördjupning" }),
    ]);
    expect(Object.values(state.groupAssignmentsByStudentId)).toHaveLength(3);
    expect(new Set(Object.values(state.groupAssignmentsByStudentId))).toEqual(
      new Set(["group-a", "group-b"]),
    );
    randomSpy.mockRestore();
  });

  it("stores student planning metadata", () => {
    const state = seedWorkspace();

    state.setStudentPlanningMeta("s1", {
      preferred_zone: "front",
      notes: "Behöver lugn plats",
    });

    expect(state.studentPlanningMetaByStudentId["s1"]?.preferred_zone).toBe("front");
    expect(state.studentPlanningMetaByStudentId["s1"]?.notes).toBe("Behöver lugn plats");
  });

  it("resolves drafts without legacy lesson-mode payload fields", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft());
    clientMocks.apiGet.mockResolvedValue(createWorkspaceResponse());

    await state.resolveDraft("roster-1", "template-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/resolve",
      {
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: "template-1",
      },
    );
    expect(clientMocks.apiPost.mock.calls[0]?.[1]).not.toHaveProperty("lesson_mode_id");
  });

  it("keeps seating workspaces alive even before a classroom has been selected", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft(null));
    clientMocks.apiGet.mockResolvedValue(createWorkspaceResponse(null));

    await state.resolveDraft("roster-1", null);

    expect(state.hasWorkspace).toBe(true);
    expect(state.template).toBeNull();
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/resolve",
      {
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: null,
      },
    );
  });

  it("starts a brand-new blank grouping draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "grouping"));
    clientMocks.apiGet.mockResolvedValue(createWorkspaceResponse("template-1", "grouping"));

    await state.startNewGroupingDraft("roster-1", "template-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new",
      {
        roster_id: "roster-1",
        template_id: "template-1",
      },
    );
    expect(state.draft?.draft_kind).toBe("grouping");
    expect(state.groupAssignments).toEqual([]);
  });

  it("starts a brand-new seating draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "seating"));
    clientMocks.apiGet.mockResolvedValue(createWorkspaceResponse("template-1", "seating"));

    await state.startNewSeatingDraft("roster-1", "template-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
      {
        roster_id: "roster-1",
        template_id: "template-1",
      },
    );
    expect(state.draft?.draft_kind).toBe("seating");
    expect(state.seatAssignments).toEqual([]);
  });

  it("activates a historical grouping draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "grouping"));
    clientMocks.apiGet.mockResolvedValue(createWorkspaceResponse("template-1", "grouping"));

    await state.activateGroupingHistoryDraft("draft-history-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/draft-history-1/activate",
    );
    expect(clientMocks.apiGet).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/workspace",
    );
    expect(state.draft?.draft_kind).toBe("grouping");
  });

  it("deletes a historical grouping draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiDelete.mockResolvedValue(undefined);

    await state.deleteGroupingHistoryDraft("draft-history-1");

    expect(clientMocks.apiDelete).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/draft-history-1",
    );
    expect(state.saveStatus).toBe("saved");
  });

  it("activates a historical seating draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "seating"));
    clientMocks.apiGet.mockResolvedValue(createWorkspaceResponse("template-1", "seating"));

    await state.activateSeatingHistoryDraft("draft-history-2");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/draft-history-2/activate",
    );
    expect(clientMocks.apiGet).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/workspace",
    );
    expect(state.draft?.draft_kind).toBe("seating");
  });

  it("deletes a historical seating draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiDelete.mockResolvedValue(undefined);

    await state.deleteSeatingHistoryDraft("draft-history-2");

    expect(clientMocks.apiDelete).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/draft-history-2",
    );
    expect(state.saveStatus).toBe("saved");
  });

  it("hydrates undo and redo availability from the backend workspace contract", async () => {
    const state = useClassroomState();
    clientMocks.apiGet.mockResolvedValue(
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

    state.renameGroup("group-a", "Handledargrupp");
    expect(state.canUndo).toBe(true);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(state.saveStatus).toBe("saved");
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

  it("autosaves only the fundamentals payload", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft();
    clientMocks.apiPatch.mockResolvedValue(createWorkspaceResponse());

    state.setStudentPlanningMeta("s1", { notes: "Fokusera nära fönstret" });
    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    const payload = clientMocks.apiPatch.mock.calls[0]?.[1];
    expect(payload).toMatchObject({
      expected_revision: 4,
      groups: state.groups,
      group_assignments: [],
      seat_assignments: [],
      student_planning_meta: [
        expect.objectContaining({
          student_id: "s1",
          notes: "Fokusera nära fönstret",
        }),
      ],
    });
    expect(payload).not.toHaveProperty("pair_constraints");
    expect(payload).not.toHaveProperty("planning_profile");
  });
});
