/**
 * Planner state-support tests.
 *
 * These tests lock the local reconciliation paths used when the teacher edits
 * the active class or classroom from modal flows while staying inside the live
 * planner workspace.
 */

import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import { createClassroomPlannerStateSupport } from "./classroomPlannerStateSupport";
import type {
  DraftGroup,
  DraftHistoryStatus,
  DraftWorkspaceResponse,
  PlanDraft,
  RelationshipRule,
  RoomTemplate,
  Roster,
  RosterSmartRulesResponse,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import type { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import type { usePlannerSessionController } from "./usePlannerSessionController";
import type { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";
import type { useSmartRuleUiState } from "./useSmartRuleUiState";

type DraftLane = ReturnType<typeof useDraftPersistenceLane>;
type PlannerSessionController = ReturnType<typeof usePlannerSessionController>;
type SmartRuleLane = ReturnType<typeof useRosterSmartRuleLane>;
type SmartRuleUiState = ReturnType<typeof useSmartRuleUiState>;

function createSupportFixture() {
  const draft = ref<PlanDraft | null>({
    id: "draft-1",
    roster_id: "roster-1",
    draft_kind: "seating",
    template_id: "template-1",
    status: "active",
    revision: 3,
    last_opened_at: "2026-03-29T10:00:00Z",
  });
  const roster = ref<Roster | null>({
    id: "roster-1",
    name: "SA24D",
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
  });
  const template = ref<RoomTemplate | null>({
    id: "template-1",
    name: "Sal 101",
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 1, y: 0, zone: null },
    ],
    fixtures: [],
  });
  const groups = ref<DraftGroup[]>([]);
  const groupAssignmentsByStudentId = ref<Record<string, string | null>>({
    "student-1": "group-a",
    "student-2": "group-a",
  });
  const seatAssignmentsByStudentId = ref<Record<string, string | null>>({
    "student-1": "seat-1",
    "student-2": "seat-2",
  });
  const seatingPreferences = ref<StudentSeatingPreference[]>([
    { student_id: "student-1", near_teacher: true },
    { student_id: "student-2", near_teacher: true },
  ]);
  const relationshipRules = ref<RelationshipRule[]>([
    { id: "rule-1", kind: "keep_near", student_ids: ["student-1", "student-2"] },
    { id: "rule-2", kind: "keep_apart", student_ids: ["student-2", "student-4"] },
  ]);
  const smartRulesRevision = ref(4);
  const historyStatus = ref<DraftHistoryStatus>({ can_undo: true, can_redo: false });
  const historyActionInFlight = ref(false);
  const smartRuleUiState = {
    reset: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
  } as unknown as SmartRuleUiState;

  const support = createClassroomPlannerStateSupport({
    draft,
    roster,
    template,
    groups,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    seatingPreferences,
    relationshipRules,
    smartRulesRevision,
    historyStatus,
    historyActionInFlight,
    groupAssignments: computed(() => []),
    seatAssignments: computed(() => []),
    sessionController: {} as PlannerSessionController,
    draftLane: {} as DraftLane,
    smartRuleLane: { applyHydratedRules: vi.fn() } as unknown as SmartRuleLane,
    smartRuleUiState,
  });

  return {
    draft,
    roster,
    template,
    groups,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    seatingPreferences,
    relationshipRules,
    smartRulesRevision,
    historyStatus,
    historyActionInFlight,
    smartRuleUiState,
    support,
  };
}

describe("createClassroomPlannerStateSupport", () => {
  it("updates the active classroom in place and drops seat assignments for removed seats", () => {
    const fixture = createSupportFixture();

    fixture.support.replaceCurrentTemplate({
      id: "template-1",
      name: "Sal 101 uppdaterad",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: "front" }],
      fixtures: [{ id: "fixture-1", type: "teacher_desk", x: 0, y: 1, width: 1, height: 1 }],
    });

    expect(fixture.template.value).toEqual({
      id: "template-1",
      name: "Sal 101 uppdaterad",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: "front" }],
      fixtures: [{ id: "fixture-1", type: "teacher_desk", x: 0, y: 1, width: 1, height: 1 }],
    });
    expect(fixture.seatAssignmentsByStudentId.value).toEqual({
      "student-1": "seat-1",
    });
  });

  it("updates the active roster in place and prunes removed students from local planner state", () => {
    const fixture = createSupportFixture();

    fixture.support.replaceCurrentRoster({
      id: "roster-1",
      name: "SA24D uppdaterad",
      students: [
        { id: "student-1", display_name: "Ada Lovelace" },
        { id: "student-3", display_name: "Grace Hopper" },
      ],
    });

    expect(fixture.roster.value).toEqual({
      id: "roster-1",
      name: "SA24D uppdaterad",
      students: [
        { id: "student-1", display_name: "Ada Lovelace" },
        { id: "student-3", display_name: "Grace Hopper" },
      ],
    });
    expect(fixture.groupAssignmentsByStudentId.value).toEqual({
      "student-1": "group-a",
    });
    expect(fixture.seatAssignmentsByStudentId.value).toEqual({
      "student-1": "seat-1",
    });
    expect(fixture.seatingPreferences.value).toEqual([
      { student_id: "student-1", near_teacher: true },
    ]);
    expect(fixture.relationshipRules.value).toEqual([]);
    expect(fixture.smartRuleUiState.reset).toHaveBeenCalledTimes(1);
  });

  it("defaults missing workspace collections to empty arrays during hydration", () => {
    const fixture = createSupportFixture();

    fixture.support.applyWorkspace({
      draft: {
        id: "draft-2",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: null,
        status: "active",
        revision: 5,
        last_opened_at: "2026-04-01T09:00:00Z",
      },
      roster: {
        id: "roster-1",
        name: "SA24D",
        students: [
          { id: "student-1", display_name: "Ada Lovelace" },
          { id: "student-2", display_name: "Alan Turing" },
        ],
      },
      template: {
        id: "template-2",
        name: "Utan stolar i payloaden",
        seats: undefined,
        fixtures: undefined,
      },
      groups: undefined,
      group_assignments: undefined,
      seat_assignments: undefined,
      history_status: {
        can_undo: false,
        can_redo: false,
      },
    } as unknown as DraftWorkspaceResponse);

    expect(fixture.groups.value).toEqual([]);
    expect(fixture.groupAssignmentsByStudentId.value).toEqual({});
    expect(fixture.seatAssignmentsByStudentId.value).toEqual({});
    expect(fixture.template.value).toEqual({
      id: "template-2",
      name: "Utan stolar i payloaden",
      seats: [],
      fixtures: [],
    });
    expect(fixture.historyStatus.value).toEqual({ can_undo: false, can_redo: false });
  });

  it("defaults missing smart-rule collections to empty arrays during hydration", () => {
    const fixture = createSupportFixture();

    fixture.support.applyRosterSmartRules({
      roster_id: "roster-1",
      revision: 7,
      seating_preferences: undefined,
      relationship_rules: undefined,
    } as unknown as RosterSmartRulesResponse);

    expect(fixture.seatingPreferences.value).toEqual([]);
    expect(fixture.relationshipRules.value).toEqual([]);
    expect(fixture.smartRulesRevision.value).toBe(7);
  });

  it("defaults missing history status during draft-save acknowledgement normalization", () => {
    const fixture = createSupportFixture();
    fixture.historyActionInFlight.value = true;

    fixture.support.applyDraftSaveAcknowledgement({
      draft: {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: null,
        status: "active",
        revision: 6,
        last_opened_at: "2026-04-01T09:30:00Z",
      },
      roster: {
        id: "roster-1",
        name: "SA24D",
        students: [
          { id: "student-1", display_name: "Ada Lovelace" },
          { id: "student-2", display_name: "Alan Turing" },
        ],
      },
      template: null,
      groups: undefined,
      group_assignments: undefined,
      seat_assignments: undefined,
      history_status: undefined,
    } as unknown as DraftWorkspaceResponse);

    expect(fixture.draft.value?.revision).toBe(6);
    expect(fixture.draft.value?.last_opened_at).toBe("2026-04-01T09:30:00Z");
    expect(fixture.historyStatus.value).toEqual({ can_undo: false, can_redo: false });
    expect(fixture.historyActionInFlight.value).toBe(false);
  });
});
