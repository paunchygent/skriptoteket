import { describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  createDraft,
  createWorkspaceResponse,
  seedWorkspace,
  setupClassroomStateTests,
} from "./useClassroomState.specSupport";

describe("useClassroomState assignment", () => {
  setupClassroomStateTests();

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
    expect(state.draftPersistenceStatus).toBe("idle");
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

  it("randomizes seating assignments across available seats and leaves overflow unplaced", () => {
    const state = seedWorkspace();
    const randomSpy = vi.spyOn(Math, "random");
    randomSpy
      .mockReturnValueOnce(0.85)
      .mockReturnValueOnce(0.1);

    state.draft = createDraft("template-1", "seating");
    state.assignStudentToSeat("s1", "seat-1");

    state.randomizeSeating();

    expect(state.seatAssignmentsByStudentId).toEqual({
      s1: "seat-2",
      s2: "seat-1",
      s3: null,
    });
    expect(state.hasPendingAutosave).toBe(true);
    randomSpy.mockRestore();
  });

  it("keeps Slumpa local when smart seating is off", async () => {
    const state = seedWorkspace();
    const randomSpy = vi.spyOn(Math, "random");
    randomSpy
      .mockReturnValueOnce(0.85)
      .mockReturnValueOnce(0.1);
    state.draft = {
      ...createDraft("template-1", "seating"),
      smart_enabled: false,
      use_history: true,
    };

    await state.runSeatingShuffle();

    expect(clientMocks.apiPost).not.toHaveBeenCalled();
    expect(state.seatAssignmentsByStudentId).toEqual({
      s1: "seat-2",
      s2: "seat-1",
      s3: null,
    });
    expect(state.smartSeatingRunMessage).toBeNull();
    randomSpy.mockRestore();
  });

  it("calls the backend smart-run endpoint when smart seating is on", async () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
      smart_enabled: true,
      use_history: true,
    };
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: {
        ...createWorkspaceResponse("template-1", "seating"),
        draft: {
          ...createDraft("template-1", "seating"),
          smart_enabled: true,
          use_history: true,
          revision: 5,
        },
        seat_assignments: [
          { student_id: "s1", seat_id: "seat-2" },
          { student_id: "s2", seat_id: "seat-1" },
        ],
      },
      used_history: true,
      message: "Smart placering klar med stöd av tidigare exporter.",
    });

    await state.runSeatingShuffle();

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/draft-1/smart-run",
      { expected_revision: 4 },
    );
    expect(state.seatAssignmentsByStudentId).toEqual({
      s1: "seat-2",
      s2: "seat-1",
    });
    expect(state.smartSeatingRunMessage).toBe(
      "Smart placering klar med stöd av tidigare exporter.",
    );
    expect(state.smartSeatingRunTone).toBe("success");
  });

  it("keeps Slumpa local when smart grouping is off", async () => {
    const state = seedWorkspace();
    const randomSpy = vi.spyOn(Math, "random");
    randomSpy
      .mockReturnValueOnce(0.85)
      .mockReturnValueOnce(0.1);
    state.draft = {
      ...createDraft("template-1", "grouping"),
      smart_enabled: false,
      use_history: true,
      grouping_seating_distance_enabled: true,
    };

    await state.runGroupingShuffle();

    expect(clientMocks.apiPost).not.toHaveBeenCalled();
    expect(Object.values(state.groupAssignmentsByStudentId).filter(Boolean)).toHaveLength(3);
    expect(state.smartGroupingRunMessage).toBeNull();
    randomSpy.mockRestore();
  });

  it("calls the backend smart-run endpoint when smart grouping is on", async () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "grouping"),
      smart_enabled: true,
      use_history: true,
      grouping_seating_distance_enabled: true,
    };
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: {
        ...createWorkspaceResponse("template-1", "grouping"),
        draft: {
          ...createDraft("template-1", "grouping"),
          smart_enabled: true,
          use_history: true,
          grouping_seating_distance_enabled: true,
          revision: 5,
        },
        group_assignments: [
          { student_id: "s1", group_id: "group-b" },
          { student_id: "s2", group_id: "group-a" },
        ],
      },
      used_history: true,
      used_live_seating: true,
      message: "Smart gruppindelning klar med historik och stöd från klassens sittschema.",
    });

    await state.runGroupingShuffle();

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/draft-1/smart-run",
      { expected_revision: 4 },
    );
    expect(state.groupAssignmentsByStudentId).toEqual({
      s1: "group-b",
      s2: "group-a",
    });
    expect(state.smartGroupingRunMessage).toBe(
      "Smart gruppindelning klar med historik och stöd från klassens sittschema.",
    );
    expect(state.smartGroupingRunTone).toBe("success");
  });

  it("clears grouping assignments in place without touching group structure", () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");
    state.groupAssignmentsByStudentId = {
      s1: "group-a",
      s2: null,
      s3: "group-b",
    };
    state.clearGroupingAssignments();

    expect(state.draft?.id).toBe("draft-1");
    expect(state.groups.map((group) => group.id)).toEqual(["group-a", "group-b"]);
    expect(state.groupAssignmentsByStudentId).toEqual({
      s1: null,
      s2: null,
      s3: null,
    });
    expect(state.hasPendingAutosave).toBe(true);
  });

  it("clears seating assignments in place without changing the selected classroom", () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.seatAssignmentsByStudentId = {
      s1: "seat-1",
      s2: null,
      s3: "seat-2",
    };
    state.clearSeatingAssignments();

    expect(state.template?.id).toBe("template-1");
    expect(state.seatAssignmentsByStudentId).toEqual({
      s1: null,
      s2: null,
      s3: null,
    });
    expect(state.hasPendingAutosave).toBe(true);
  });

  it("does not dirty the draft when börja om is used on an already empty workspace", () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");

    state.clearGroupingAssignments();
    state.clearSeatingAssignments();

    expect(state.hasPendingAutosave).toBe(false);
    expect(state.draftPersistenceStatus).toBe("idle");
  });
});
