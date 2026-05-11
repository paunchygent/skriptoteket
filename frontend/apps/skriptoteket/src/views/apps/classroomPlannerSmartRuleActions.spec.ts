/**
 * Classroom planner smart-rule action tests.
 *
 * Purpose:
 *   Lock direct smart-rule mutations that sit below the rules workspace UI.
 *
 * Relationships:
 *   - covers `classroomPlannerSmartRuleActions.ts`
 *   - uses the real smart-rule UI bucket for fixed-seat authoring state
 */

import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import { createClassroomPlannerSmartRuleActions } from "./classroomPlannerSmartRuleActions";
import type {
  FixedSeatRule,
  PlanDraft,
  RelationshipRule,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import { useSmartRuleUiState } from "./useSmartRuleUiState";
import type { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import type { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";

type DraftLane = ReturnType<typeof useDraftPersistenceLane>;
type SmartRuleLane = ReturnType<typeof useRosterSmartRuleLane>;

function createFixture(input: {
  initialFixedSeatRules?: FixedSeatRule[];
  draft?: PlanDraft | null;
} = {}) {
  const draft = ref<PlanDraft | null>(input.draft ?? null);
  const fixedSeatRules = ref<FixedSeatRule[]>(input.initialFixedSeatRules ?? []);
  const draftLane = {
    markDirty: vi.fn(),
  } as unknown as DraftLane;
  const smartRuleLane = {
    markDirty: vi.fn(),
  } as unknown as SmartRuleLane;
  const smartRuleUiState = useSmartRuleUiState({
    canEditSmartRules: () => true,
  });
  const clearRuleDiagnostics = vi.fn();
  const actions = createClassroomPlannerSmartRuleActions({
    draft,
    template: ref({
      id: "template-1",
      name: "Sal 101",
      seats: [
        { id: "seat-1", x: 0, y: 0, zone: null },
        { id: "seat-2", x: 1, y: 0, zone: null },
      ],
      fixtures: [],
    }),
    seatingPreferences: ref<StudentSeatingPreference[]>([]),
    relationshipRules: ref<RelationshipRule[]>([]),
    fixedSeatRules,
    studentsById: computed(() => ({
      "student-1": { id: "student-1" },
      "student-2": { id: "student-2" },
    })),
    seatsById: computed(() => ({
      "seat-1": { id: "seat-1" },
      "seat-2": { id: "seat-2" },
    })),
    isWorkspaceBusy: computed(() => false),
    canEditSeatingSmartRules: computed(() => true),
    draftLane,
    smartRuleLane,
    smartRuleUiState,
    syncVisibleSessionBindings: vi.fn(),
    clearRuleDiagnostics,
  });
  return { actions, clearRuleDiagnostics, draft, draftLane, fixedSeatRules, smartRuleLane, smartRuleUiState };
}

describe("createClassroomPlannerSmartRuleActions", () => {
  it("treats missing grouping seating influence flag as disabled until the teacher opts in", () => {
    const fixture = createFixture({
      draft: {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "grouping",
        status: "active",
        revision: 1,
        last_opened_at: "2026-05-06T10:00:00.000Z",
      },
    });

    fixture.actions.setDraftGroupingSeatingDistanceEnabled(false);

    expect(fixture.draft.value?.grouping_seating_distance_enabled).toBeUndefined();
    expect(fixture.draftLane.markDirty).not.toHaveBeenCalled();

    fixture.actions.setDraftGroupingSeatingDistanceEnabled(true);

    expect(fixture.draft.value?.grouping_seating_distance_enabled).toBe(true);
    expect(fixture.draftLane.markDirty).toHaveBeenCalledTimes(1);
    expect(fixture.clearRuleDiagnostics).toHaveBeenCalledTimes(1);
  });

  it("clears stored solver diagnostics when direct smart-rule mutations change rules", () => {
    const fixture = createFixture();

    expect(fixture.actions.setStudentNearTeacherEnabled("student-1", true)).toBe(true);

    fixture.smartRuleUiState.setActiveSeatingSmartTool("keep_near");
    fixture.actions.handleSeatingSmartToolStudentSelection("student-1");
    fixture.actions.handleSeatingSmartToolStudentSelection("student-2");
    expect(fixture.actions.commitPendingRelationshipRule()).toBe(true);

    fixture.smartRuleUiState.setActiveSeatingSmartTool("fixed_seat");
    fixture.actions.handleSeatingSmartToolStudentSelection("student-1");
    fixture.actions.selectFixedSeatRuleSeat("seat-1");
    expect(fixture.actions.commitPendingFixedSeatRule()).toBe(true);

    expect(fixture.clearRuleDiagnostics).toHaveBeenCalledTimes(3);
  });

  it("creates fixed-seat rules only after seat selection and explicit confirmation", () => {
    const fixture = createFixture();

    fixture.smartRuleUiState.setActiveSeatingSmartTool("fixed_seat");
    expect(fixture.actions.handleSeatingSmartToolStudentSelection("student-1")).toBe(true);
    expect(fixture.actions.selectFixedSeatRuleSeat("seat-1")).toBe(true);

    expect(fixture.fixedSeatRules.value).toEqual([]);
    expect(fixture.smartRuleUiState.canCommitPendingFixedSeatRule.value).toBe(true);
    expect(fixture.actions.commitPendingFixedSeatRule()).toBe(true);

    expect(fixture.fixedSeatRules.value).toHaveLength(1);
    expect(fixture.fixedSeatRules.value[0]).toMatchObject({
      template_id: "template-1",
      student_id: "student-1",
      seat_id: "seat-1",
    });
    expect(fixture.smartRuleUiState.pendingFixedSeatStudentId.value).toBeNull();
    expect(fixture.smartRuleUiState.pendingFixedSeatSeatId.value).toBeNull();
    expect(fixture.smartRuleLane.markDirty).toHaveBeenCalledTimes(1);
  });

  it("deletes fixed-seat rules through the shared smart-rule mutation path", () => {
    const fixture = createFixture({
      initialFixedSeatRules: [
        {
          id: "fixed-1",
          template_id: "template-1",
          student_id: "student-1",
          seat_id: "seat-1",
        },
        {
          id: "fixed-2",
          template_id: "template-1",
          student_id: "student-2",
          seat_id: "seat-2",
        },
      ],
    });

    fixture.actions.beginFixedSeatRuleEdit("fixed-1");
    fixture.actions.deleteFixedSeatRule("missing-rule");

    expect(fixture.fixedSeatRules.value).toHaveLength(2);
    expect(fixture.smartRuleLane.markDirty).not.toHaveBeenCalled();

    fixture.actions.deleteFixedSeatRule("fixed-1");

    expect(fixture.fixedSeatRules.value).toEqual([
      {
        id: "fixed-2",
        template_id: "template-1",
        student_id: "student-2",
        seat_id: "seat-2",
      },
    ]);
    expect(fixture.smartRuleUiState.editingFixedSeatRuleId.value).toBeNull();
    expect(fixture.smartRuleLane.markDirty).toHaveBeenCalledTimes(1);
    expect(fixture.clearRuleDiagnostics).toHaveBeenCalledTimes(1);
  });

  it("toggles fixed-seat student and seat selections before confirmation", () => {
    const fixture = createFixture();

    fixture.smartRuleUiState.setActiveSeatingSmartTool("fixed_seat");
    fixture.actions.handleSeatingSmartToolStudentSelection("student-1");
    fixture.actions.selectFixedSeatRuleSeat("seat-1");

    expect(fixture.smartRuleUiState.pendingFixedSeatStudentId.value).toBe("student-1");
    expect(fixture.smartRuleUiState.pendingFixedSeatSeatId.value).toBe("seat-1");

    fixture.actions.handleSeatingSmartToolStudentSelection("student-1");
    fixture.actions.selectFixedSeatRuleSeat("seat-1");

    expect(fixture.smartRuleUiState.pendingFixedSeatStudentId.value).toBeNull();
    expect(fixture.smartRuleUiState.pendingFixedSeatSeatId.value).toBeNull();
    expect(fixture.smartRuleUiState.canCommitPendingFixedSeatRule.value).toBe(false);
  });

  it("moves an existing fixed-seat rule after editing and confirmation", () => {
    const fixture = createFixture({
      initialFixedSeatRules: [
      {
        id: "fixed-1",
        template_id: "template-1",
        student_id: "student-1",
        seat_id: "seat-1",
      },
    ]});

    fixture.actions.beginFixedSeatRuleEdit("fixed-1");
    expect(fixture.smartRuleUiState.pendingFixedSeatStudentId.value).toBe("student-1");
    expect(fixture.smartRuleUiState.pendingFixedSeatSeatId.value).toBe("seat-1");
    fixture.actions.selectFixedSeatRuleSeat("seat-2");
    expect(fixture.actions.commitPendingFixedSeatRule()).toBe(true);

    expect(fixture.fixedSeatRules.value).toHaveLength(1);
    expect(fixture.fixedSeatRules.value[0]).toMatchObject({
      id: "fixed-1",
      student_id: "student-1",
      seat_id: "seat-2",
    });
  });

  it("blocks locking a seat already fixed for another student", () => {
    const fixture = createFixture({
      initialFixedSeatRules: [
      {
        id: "fixed-1",
        template_id: "template-1",
        student_id: "student-1",
        seat_id: "seat-1",
      },
    ]});

    fixture.smartRuleUiState.setActiveSeatingSmartTool("fixed_seat");
    fixture.actions.handleSeatingSmartToolStudentSelection("student-2");
    fixture.actions.selectFixedSeatRuleSeat("seat-1");

    expect(fixture.actions.commitPendingFixedSeatRule()).toBe(false);
    expect(fixture.smartRuleUiState.feedbackMessage.value).toBe(
      "Platsen är redan låst. Välj en annan plats.",
    );
    expect(fixture.fixedSeatRules.value).toHaveLength(1);
  });
});
