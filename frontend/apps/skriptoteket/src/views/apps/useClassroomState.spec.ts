import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useClassroomState } from "./useClassroomState";
import type { DraftWorkspaceResponse, RosterSmartRulesResponse } from "./classroomPlannerTypes";

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
): DraftWorkspaceResponse {
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
    history_status: historyStatus,
  };
}

function createSmartRulesResponse(): RosterSmartRulesResponse {
  return {
    roster_id: "roster-1",
    revision: 0,
    seating_preferences: [],
    relationship_rules: [],
  };
}

function createWorkspaceVariant(options: {
  draftId?: string;
  rosterId?: string;
  templateId?: string | null;
  draftKind?: "seating" | "grouping";
  historyStatus?: { can_undo: boolean; can_redo: boolean };
} = {}): DraftWorkspaceResponse {
  const workspace = createWorkspaceResponse(
    options.templateId ?? "template-1",
    options.draftKind ?? "seating",
    options.historyStatus,
  );
  const rosterId = options.rosterId ?? workspace.roster.id;
  const draftId = options.draftId ?? workspace.draft.id;
  return {
    ...workspace,
    draft: {
      ...workspace.draft,
      id: draftId,
      roster_id: rosterId,
      template_id: options.templateId ?? workspace.draft.template_id,
    },
    roster: {
      ...workspace.roster,
      id: rosterId,
    },
    template:
      options.templateId === null
        ? null
        : workspace.template,
  };
}

function createDeferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
}

function mockWorkspaceLoad(
  workspace = createWorkspaceResponse(),
  smartRules = createSmartRulesResponse(),
): void {
  clientMocks.apiGet.mockResolvedValueOnce(workspace);
  clientMocks.apiGet.mockResolvedValueOnce(smartRules);
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
  state.smartRulesRevision = 0;
  state.smartRuleHydrationStatus = "ready";
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

  it("tracks the active seating smart tool and clears pending relation selections on tool change", () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
    };

    state.setActiveSeatingSmartTool("keep_apart");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.handleSeatingSmartToolStudentSelection("s2");

    expect(state.activeSeatingSmartTool).toBe("keep_apart");
    expect(state.pendingRelationshipStudentIds).toEqual(["s1", "s2"]);

    state.setActiveSeatingSmartTool("keep_near");

    expect(state.activeSeatingSmartTool).toBe("keep_near");
    expect(state.pendingRelationshipStudentIds).toEqual([]);
  });

  it("keeps near-teacher selections pending until the teacher confirms the rule", () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
    };

    state.setActiveSeatingSmartTool("near_teacher");

    expect(state.handleSeatingSmartToolStudentSelection("s1")).toBe(true);
    expect(state.pendingRelationshipStudentIds).toEqual(["s1"]);
    expect(state.seatingPreferences).toEqual([]);
    expect(state.hasPendingAutosave).toBe(false);

    expect(state.commitPendingRelationshipRule()).toBe(true);
    expect(state.seatingPreferences).toEqual([
      {
        student_id: "s1",
        near_teacher: true,
      },
    ]);
    expect(state.hasPendingAutosave).toBe(true);

    state.discardPendingSessionWork();
    state.beginNearTeacherEdit();
    expect(state.handleSeatingSmartToolStudentSelection("s1")).toBe(true);
    expect(state.pendingRelationshipStudentIds).toEqual([]);
    expect(state.commitPendingRelationshipRule()).toBe(false);
    expect(state.seatingPreferences).toEqual([
      {
        student_id: "s1",
        near_teacher: true,
      },
    ]);
    expect(state.clearNearTeacherRule()).toBe(true);
    expect(state.seatingPreferences).toEqual([]);
  });

  it("creates one visible relation cluster from a temporary smart-rule selection", () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
    };

    state.setActiveSeatingSmartTool("keep_apart");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.handleSeatingSmartToolStudentSelection("s2");
    state.handleSeatingSmartToolStudentSelection("s3");

    expect(state.canCommitPendingRelationshipRule).toBe(true);
    expect(state.commitPendingRelationshipRule()).toBe(true);

    expect(state.activeSeatingSmartTool).toBe("keep_apart");
    expect(state.pendingRelationshipStudentIds).toEqual([]);
    expect(state.relationshipRules).toEqual([
      expect.objectContaining({
        kind: "keep_apart",
        student_ids: ["s1", "s2", "s3"],
      }),
    ]);
    expect(state.hasPendingAutosave).toBe(true);
  });

  it("blocks overlapping relation clusters with a teacher-facing explanation", () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
    };
    state.relationshipRules = [
      {
        id: "rule-1",
        kind: "keep_apart",
        student_ids: ["s1", "s2"],
      },
    ];

    state.setActiveSeatingSmartTool("keep_near");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.handleSeatingSmartToolStudentSelection("s3");

    expect(state.commitPendingRelationshipRule()).toBe(false);
    expect(state.relationshipRules).toHaveLength(1);
    expect(state.smartRuleFeedbackMessage).toBe(
      "En elev kan bara ingå i en relationsregel åt gången.",
    );
  });

  it("keeps the active smart tool selected after autosave reconciliation", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
    };
    clientMocks.apiPatch.mockResolvedValue({
      ...createSmartRulesResponse(),
      relationship_rules: [
        {
          id: "rule-1",
          kind: "keep_apart",
          student_ids: ["s1", "s2"],
        },
      ],
    });

    state.setActiveSeatingSmartTool("keep_apart");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.handleSeatingSmartToolStudentSelection("s2");
    expect(state.commitPendingRelationshipRule()).toBe(true);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(clientMocks.apiPatch).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
      {
        expected_revision: 0,
        seating_preferences: [],
        relationship_rules: [
          expect.objectContaining({
            kind: "keep_apart",
            student_ids: ["s1", "s2"],
          }),
        ],
      },
    );
    expect(state.activeSeatingSmartTool).toBe("keep_apart");
  });

  it("persists relationship-rule edits through the roster smart-rules lane without changing the rule id", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.smartRulesRevision = 4;
    state.relationshipRules = [
      {
        id: "rule-1",
        kind: "keep_apart",
        student_ids: ["s1", "s2"],
      },
    ];
    clientMocks.apiPatch.mockResolvedValue({
      ...createSmartRulesResponse(),
      revision: 5,
      relationship_rules: [
        {
          id: "rule-1",
          kind: "keep_apart",
          student_ids: ["s1", "s3"],
        },
      ],
    });

    state.beginRelationshipRuleEdit("rule-1");
    state.handleSeatingSmartToolStudentSelection("s2");
    state.handleSeatingSmartToolStudentSelection("s3");

    expect(state.pendingRelationshipStudentIds).toEqual(["s1", "s3"]);
    expect(state.commitPendingRelationshipRule()).toBe(true);
    expect(state.relationshipRules).toEqual([
      {
        id: "rule-1",
        kind: "keep_apart",
        student_ids: ["s1", "s3"],
      },
    ]);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
      {
        expected_revision: 4,
        seating_preferences: [],
        relationship_rules: [
          {
            id: "rule-1",
            kind: "keep_apart",
            student_ids: ["s1", "s3"],
          },
        ],
      },
    );
    expect(state.smartRulesRevision).toBe(5);
    expect(state.relationshipRules).toEqual([
      {
        id: "rule-1",
        kind: "keep_apart",
        student_ids: ["s1", "s3"],
      },
    ]);
  });

  it("persists near-teacher replacement edits through the roster smart-rules lane", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.smartRulesRevision = 1;
    state.seatingPreferences = [{ student_id: "s1", near_teacher: true }];
    clientMocks.apiPatch.mockResolvedValue({
      ...createSmartRulesResponse(),
      revision: 2,
      seating_preferences: [{ student_id: "s2", near_teacher: true }],
    });

    expect(state.replaceNearTeacherPreference("s1", "s2")).toBe(true);
    expect(state.seatingPreferences).toEqual([{ student_id: "s2", near_teacher: true }]);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
      {
        expected_revision: 1,
        seating_preferences: [{ student_id: "s2", near_teacher: true }],
        relationship_rules: [],
      },
    );
    expect(state.smartRulesRevision).toBe(2);
    expect(state.seatingPreferences).toEqual([{ student_id: "s2", near_teacher: true }]);
  });

  it("removes near-teacher rules through the roster smart-rules lane when the inspector disables them", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.smartRulesRevision = 6;
    state.seatingPreferences = [
      { student_id: "s1", near_teacher: true },
      { student_id: "s3", near_teacher: true },
    ];
    clientMocks.apiPatch.mockResolvedValue({
      ...createSmartRulesResponse(),
      revision: 7,
      seating_preferences: [{ student_id: "s3", near_teacher: true }],
    });

    expect(state.setStudentNearTeacherEnabled("s1", false)).toBe(true);
    expect(state.seatingPreferences).toEqual([{ student_id: "s3", near_teacher: true }]);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
      {
        expected_revision: 6,
        seating_preferences: [{ student_id: "s3", near_teacher: true }],
        relationship_rules: [],
      },
    );
    expect(state.smartRulesRevision).toBe(7);
    expect(state.seatingPreferences).toEqual([{ student_id: "s3", near_teacher: true }]);
  });

  it("does not delete a relationship rule while the workspace is busy", async () => {
    const state = seedWorkspace();
    state.relationshipRules = [
      {
        id: "rule-1",
        kind: "keep_apart",
        student_ids: ["s1", "s2"],
      },
    ];
    let resolveWorkspace!: (value: ReturnType<typeof createWorkspaceResponse>) => void;
    clientMocks.apiGet.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveWorkspace = resolve;
        }),
    );
    clientMocks.apiGet.mockResolvedValueOnce(createSmartRulesResponse());

    const loadPromise = state.loadWorkspace("draft-1");

    expect(state.isWorkspaceBusy).toBe(true);
    state.deleteRelationshipRule("rule-1");

    expect(state.relationshipRules).toEqual([
      {
        id: "rule-1",
        kind: "keep_apart",
        student_ids: ["s1", "s2"],
      },
    ]);

    resolveWorkspace(createWorkspaceResponse("template-1", "seating"));
    await loadPromise;
  });

  it("loads roster smart rules separately from the draft workspace contract", async () => {
    const state = useClassroomState();
    mockWorkspaceLoad(
      createWorkspaceResponse(),
      {
        ...createSmartRulesResponse(),
        seating_preferences: [{ student_id: "s2", near_teacher: true }],
        relationship_rules: [
          {
            id: "rule-1",
            kind: "keep_near",
            student_ids: ["s1", "s3"],
          },
        ],
      },
    );

    await state.loadWorkspace("draft-1");

    expect(clientMocks.apiGet).toHaveBeenNthCalledWith(
      1,
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/workspace",
    );
    expect(clientMocks.apiGet).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
    );
    expect(state.seatingPreferences).toEqual([{ student_id: "s2", near_teacher: true }]);
    expect(state.relationshipRules).toEqual([
      {
        id: "rule-1",
        kind: "keep_near",
        student_ids: ["s1", "s3"],
      },
    ]);
    expect(state.smartRulesRevision).toBe(0);
    expect(state.smartRulesHydrated).toBe(true);
  });

  it("clears stale smart rules and disables authoring when the follow-up smart-rule load fails", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.seatingPreferences = [{ student_id: "s1", near_teacher: true }];
    state.relationshipRules = [{ id: "rule-old", kind: "keep_apart", student_ids: ["s1", "s2"] }];
    state.smartRulesRevision = 5;
    const workspace = createWorkspaceResponse();
    workspace.roster = {
      id: "roster-2",
      name: "Klass 9B",
      students: workspace.roster.students,
    };
    clientMocks.apiGet.mockResolvedValueOnce(workspace);
    clientMocks.apiGet.mockRejectedValueOnce(new Error("Kunde inte ladda smarta regler."));

    await state.loadWorkspace("draft-2");

    expect(clientMocks.apiGet).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-2/smart-rules",
    );
    expect(state.roster?.id).toBe("roster-2");
    expect(state.seatingPreferences).toEqual([]);
    expect(state.relationshipRules).toEqual([]);
    expect(state.smartRulesRevision).toBe(0);
    expect(state.smartRulesHydrated).toBe(false);
    expect(state.canEditSeatingSmartRules).toBe(false);
    expect(state.smartRuleHydrationStatus).toBe("error");
  });

  it("ignores a late workspace load after the workspace has been cleared", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const workspaceDeferred = createDeferred<ReturnType<typeof createWorkspaceResponse>>();
    clientMocks.apiGet.mockReturnValueOnce(workspaceDeferred.promise);

    const loadPromise = state.loadWorkspace("draft-2");

    state.clearWorkspace();
    workspaceDeferred.resolve(createWorkspaceResponse());
    await loadPromise;

    expect(state.draft).toBeNull();
    expect(state.roster).toBeNull();
    expect(state.template).toBeNull();
    expect(clientMocks.apiGet).toHaveBeenCalledTimes(1);
  });

  it("lets teachers author smart rules even when draft-level smart mode is off", () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
      smart_enabled: false,
    };

    state.setActiveSeatingSmartTool("near_teacher");

    expect(state.activeSeatingSmartTool).toBe("near_teacher");
    expect(state.handleSeatingSmartToolStudentSelection("s1")).toBe(true);
    expect(state.pendingRelationshipStudentIds).toEqual(["s1"]);
    expect(state.commitPendingRelationshipRule()).toBe(true);
    expect(state.seatingPreferences).toEqual([{ student_id: "s1", near_teacher: true }]);
  });

  it("does not let a late autosave response repopulate cleared workspace state", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const draftPatchDeferred = createDeferred<ReturnType<typeof createWorkspaceResponse>>();
    clientMocks.apiPatch.mockReturnValueOnce(draftPatchDeferred.promise);
    vi.useFakeTimers();

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();
    state.clearWorkspace();

    draftPatchDeferred.resolve(createWorkspaceResponse());
    await Promise.resolve();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    expect(state.draft).toBeNull();
    expect(state.roster).toBeNull();
    expect(state.template).toBeNull();
    expect(state.draftPersistenceStatus).toBe("idle");
    expect(state.plannerStatusMessage).toBeNull();
  });

  it("ignores a late draft autosave response after switching to another workspace", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const draftPatchDeferred = createDeferred<ReturnType<typeof createWorkspaceVariant>>();
    clientMocks.apiPatch.mockReturnValueOnce(draftPatchDeferred.promise);
    clientMocks.apiGet.mockResolvedValueOnce(
      createWorkspaceVariant({
        draftId: "draft-2",
        rosterId: "roster-2",
      }),
    );
    clientMocks.apiGet.mockResolvedValueOnce({
      ...createSmartRulesResponse(),
      roster_id: "roster-2",
      seating_preferences: [{ student_id: "s2", near_teacher: true }],
    });

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();

    const loadPromise = state.loadWorkspace("draft-2");
    await Promise.resolve();

    draftPatchDeferred.resolve(
      createWorkspaceVariant({
        draftId: "draft-1",
        rosterId: "roster-1",
      }),
    );
    await Promise.resolve();
    await loadPromise;

    expect(state.draft?.id).toBe("draft-2");
    expect(state.roster?.id).toBe("roster-2");
    expect(state.seatingPreferences).toEqual([{ student_id: "s2", near_teacher: true }]);
    expect(state.seatAssignmentsByStudentId).toEqual({});
  });

  it("keeps newer draft edits dirty when an older draft autosave succeeds first", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const firstDraftSave = createDeferred<ReturnType<typeof createWorkspaceVariant>>();
    clientMocks.apiPatch
      .mockReturnValueOnce(firstDraftSave.promise)
      .mockResolvedValueOnce({
        ...createWorkspaceVariant(),
        draft: {
          ...createWorkspaceVariant().draft,
          revision: 6,
        },
        seat_assignments: [{ student_id: "s1", seat_id: "seat-2" }],
      });

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();

    state.assignStudentToSeat("s1", "seat-2");
    firstDraftSave.resolve({
      ...createWorkspaceVariant(),
      draft: {
        ...createWorkspaceVariant().draft,
        revision: 5,
      },
      seat_assignments: [{ student_id: "s1", seat_id: "seat-1" }],
    });
    await Promise.resolve();

    expect(state.seatAssignmentsByStudentId["s1"]).toBe("seat-2");
    expect(state.hasPendingAutosave).toBe(true);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(clientMocks.apiPatch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1",
      expect.objectContaining({
        expected_revision: 5,
        seat_assignments: [{ student_id: "s1", seat_id: "seat-2" }],
      }),
    );
    expect(state.seatAssignmentsByStudentId["s1"]).toBe("seat-2");
    expect(state.draft?.revision).toBe(6);
    expect(state.hasPendingAutosave).toBe(false);
  });

  it("keeps newer smart-rule edits dirty when an older smart-rule autosave succeeds first", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const firstSmartRuleSave = createDeferred<RosterSmartRulesResponse>();
    clientMocks.apiPatch
      .mockReturnValueOnce(firstSmartRuleSave.promise)
      .mockResolvedValueOnce({
        ...createSmartRulesResponse(),
        revision: 2,
        seating_preferences: [
          { student_id: "s1", near_teacher: true },
          { student_id: "s2", near_teacher: true },
        ],
      });

    state.setActiveSeatingSmartTool("near_teacher");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.commitPendingRelationshipRule();
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();

    state.beginNearTeacherEdit();
    state.handleSeatingSmartToolStudentSelection("s2");
    state.commitPendingRelationshipRule();
    firstSmartRuleSave.resolve({
      ...createSmartRulesResponse(),
      revision: 1,
      seating_preferences: [{ student_id: "s1", near_teacher: true }],
    });
    await Promise.resolve();

    expect(state.seatingPreferences).toEqual([
      { student_id: "s1", near_teacher: true },
      { student_id: "s2", near_teacher: true },
    ]);
    expect(state.hasPendingAutosave).toBe(true);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(clientMocks.apiPatch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
      {
        expected_revision: 1,
        seating_preferences: [
          { student_id: "s1", near_teacher: true },
          { student_id: "s2", near_teacher: true },
        ],
        relationship_rules: [],
      },
    );
    expect(state.smartRulesRevision).toBe(2);
    expect(state.seatingPreferences).toEqual([
      { student_id: "s1", near_teacher: true },
      { student_id: "s2", near_teacher: true },
    ]);
    expect(state.hasPendingAutosave).toBe(false);
  });

  it("filters false-valued near-teacher entries when hydrating roster smart rules", async () => {
    const state = useClassroomState();
    mockWorkspaceLoad(
      createWorkspaceResponse(),
      {
        ...createSmartRulesResponse(),
        seating_preferences: [{ student_id: "s2", near_teacher: false }],
      },
    );

    await state.loadWorkspace("draft-1");

    expect(state.seatingPreferences).toEqual([]);
    expect(state.isStudentMarkedNearTeacher("s2")).toBe(false);
  });

  it("resolves drafts without legacy lesson-mode payload fields", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft());
    mockWorkspaceLoad(createWorkspaceResponse());

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
    mockWorkspaceLoad(createWorkspaceResponse(null));

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
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "grouping"));

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
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "seating"));

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
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "grouping"));

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
  });

  it("activates a historical seating draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "seating"));
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "seating"));

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
  });

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

  it("autosaves only the fundamentals payload", async () => {
    vi.useFakeTimers();
    const state = useClassroomState();
    mockWorkspaceLoad(
      createWorkspaceResponse(),
      {
        ...createSmartRulesResponse(),
        seating_preferences: [
          {
            student_id: "s2",
            near_teacher: true,
          },
        ],
      },
    );
    clientMocks.apiPatch.mockResolvedValue(createWorkspaceResponse());
    await state.loadWorkspace("draft-1");
    clientMocks.apiPatch.mockClear();

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    const payload = clientMocks.apiPatch.mock.calls[0]?.[1];
    expect(payload).toMatchObject({
      expected_revision: 4,
      groups: state.groups,
      group_assignments: [],
      seat_assignments: [{ student_id: "s1", seat_id: "seat-1" }],
    });
    expect(payload).not.toHaveProperty("seating_preferences");
    expect(payload).not.toHaveProperty("relationship_rules");
    expect(payload).not.toHaveProperty("pair_constraints");
    expect(payload).not.toHaveProperty("planning_profile");
  });

  it("keeps draft autosave dirty when smart-rule autosave fails and retries that lane on flush", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.smartRulesRevision = 4;
    let smartRuleSaveAttempts = 0;
    clientMocks.apiPatch.mockImplementation(async (url: string) => {
      if (url.endsWith("/smart-rules")) {
        smartRuleSaveAttempts += 1;
        if (smartRuleSaveAttempts === 1) {
          throw new Error("smart rules unavailable");
        }
        return {
          ...createSmartRulesResponse(),
          roster_id: "roster-1",
          revision: 5,
          seating_preferences: [{ student_id: "s1", near_teacher: true }],
          relationship_rules: [],
        };
      }
      if (url.endsWith("/drafts/draft-1")) {
        return createWorkspaceResponse("template-1", "seating", {
          can_undo: false,
          can_redo: false,
        });
      }
      throw new Error(`Unexpected patch url: ${url}`);
    });

    state.assignStudentToSeat("s1", "seat-1");
    state.setActiveSeatingSmartTool("near_teacher");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.commitPendingRelationshipRule();

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(clientMocks.apiPatch.mock.calls.map((call) => call[0])).toEqual(
      expect.arrayContaining([
        "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
        "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1",
      ]),
    );
    expect(state.hasPendingAutosave).toBe(true);
    expect(state.smartRulePersistenceStatus).toBe("error");
    expect(state.draftPersistenceStatus).toBe("saved");

    const flushResult = await state.prepareForWorkspaceSwitch({
      conflictMessage: "unused",
      fallbackMessage: "unused",
    });

    expect(flushResult).toEqual({ status: "saved", message: null });
    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(3);
    expect(clientMocks.apiPatch.mock.calls[2]?.[0]).toBe(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
    );
    expect(clientMocks.apiPatch.mock.calls[2]?.[1]).toMatchObject({
      expected_revision: 4,
      seating_preferences: [{ student_id: "s1", near_teacher: true }],
      relationship_rules: [],
    });
    expect(state.hasPendingAutosave).toBe(false);
    expect(state.smartRulesRevision).toBe(5);
    expect(state.smartRulePersistenceStatus).toBe("saved");
  });
});
