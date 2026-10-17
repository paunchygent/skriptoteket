import { describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  createDraft,
  createWorkspaceResponse,
  createSmartRulesResponse,
  mockWorkspaceLoad,
  seedWorkspace,
  setupClassroomStateTests,
} from "./useClassroomState.specSupport";
import { useClassroomState } from "./useClassroomState";

describe("useClassroomState smartRules", () => {
  setupClassroomStateTests();

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

  it("removes pending rule candidates idempotently without mutating persisted rules", () => {
    const state = seedWorkspace();
    state.draft = {
      ...createDraft("template-1", "seating"),
    };
    state.relationshipRules = [
      { id: "rule-1", kind: "keep_near", student_ids: ["s1", "s2"] },
    ];

    state.beginRelationshipRuleEdit("rule-1");

    expect(state.pendingRelationshipStudentIds).toEqual(["s1", "s2"]);
    expect(state.isStudentInPendingRuleCandidates("s1")).toBe(true);

    state.removePendingRuleCandidate("s1");
    state.removePendingRuleCandidate("s1");

    expect(state.pendingRelationshipStudentIds).toEqual(["s2"]);
    expect(state.editingRelationshipRuleId).toBe("rule-1");
    expect(state.relationshipRules).toEqual([
      { id: "rule-1", kind: "keep_near", student_ids: ["s1", "s2"] },
    ]);
    expect(state.hasPendingAutosave).toBe(false);
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
        fixed_seat_rules: [],
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
        fixed_seat_rules: [],
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
        fixed_seat_rules: [],
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
        fixed_seat_rules: [],
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
});
