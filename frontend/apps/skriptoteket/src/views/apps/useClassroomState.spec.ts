import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useClassroomState } from "./useClassroomState";

const clientMocks = vi.hoisted(() => ({
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
    apiGet: clientMocks.apiGet,
    apiPatch: clientMocks.apiPatch,
    apiPost: clientMocks.apiPost,
    isApiError: clientMocks.isApiError,
  };
});

function createDraft() {
  return {
    id: "draft-1",
    roster_id: "roster-1",
    draft_kind: "seating" as const,
    template_id: "template-1",
    status: "active" as const,
    revision: 4,
    last_opened_at: "2026-03-21T10:00:00Z",
  };
}

function createWorkspaceResponse() {
  return {
    draft: createDraft(),
    roster: {
      id: "roster-1",
      name: "Klass 9A",
      students: [
        { id: "s1", display_name: "Student 1" },
        { id: "s2", display_name: "Student 2" },
        { id: "s3", display_name: "Student 3" },
      ],
    },
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [
        { id: "seat-1", x: 0, y: 0, zone: "front" },
        { id: "seat-2", x: 120, y: 0, zone: "front" },
      ],
      fixtures: [],
    },
    groups: [
      { id: "group-a", name: "Grupp A", sort_order: 0 },
      { id: "group-b", name: "Grupp B", sort_order: 1 },
    ],
    group_assignments: [],
    seat_assignments: [],
    student_planning_meta: [],
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
    { id: "group-a", name: "Grupp A", sort_order: 0 },
    { id: "group-b", name: "Grupp B", sort_order: 1 },
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

    expect(state.groups.find((group) => group.id === createdGroup!.id)?.name).toBe("Nya Grupp C");

    state.removeGroup(createdGroup!.id);

    expect(state.groups.find((group) => group.id === createdGroup!.id)).toBeUndefined();
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

  it("autosaves only the fundamentals payload", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft();
    clientMocks.apiPatch.mockResolvedValue({ ...createDraft(), revision: 5 });

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
