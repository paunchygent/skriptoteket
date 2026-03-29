/**
 * Classroom planner state support.
 *
 * Purpose:
 *   Keep workspace application, persistence serialization, teardown, and lane
 *   synchronization logic out of `useClassroomState.ts` so the Pinia store can
 *   stay focused on composition.
 *
 * Relationships:
 *   - consumed by `useClassroomState.ts`
 *   - bridges local planner refs with the draft and smart-rule persistence
 *     lanes
 *   - exposes transition-controller helpers used by
 *     `plannerTransitionPolicies.ts`
 */

import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../../api/client";
import { discardPlannerSession } from "./plannerTransitionPolicies";
import { normalizeAssignments, reindexGroups } from "./classroomPlannerStoreMutations";
import type {
  DraftHistoryStatus,
  DraftGroup,
  DraftWorkspaceResponse,
  GroupAssignment,
  PlanDraft,
  RelationshipRule,
  RoomTemplate,
  Roster,
  RosterSmartRulesResponse,
  SeatAssignment,
  StudentPlanningMeta,
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

type CreateClassroomPlannerStateSupportOptions = {
  draft: Ref<PlanDraft | null>;
  roster: Ref<Roster | null>;
  template: Ref<RoomTemplate | null>;
  groups: Ref<DraftGroup[]>;
  groupAssignmentsByStudentId: Ref<Record<string, string | null>>;
  seatAssignmentsByStudentId: Ref<Record<string, string | null>>;
  studentPlanningMetaByStudentId: Ref<Record<string, StudentPlanningMeta>>;
  seatingPreferences: Ref<StudentSeatingPreference[]>;
  relationshipRules: Ref<RelationshipRule[]>;
  smartRulesRevision: Ref<number>;
  historyStatus: Ref<DraftHistoryStatus>;
  historyActionInFlight: Ref<boolean>;
  studentPlanningMeta: ComputedRef<StudentPlanningMeta[]>;
  groupAssignments: ComputedRef<GroupAssignment[]>;
  seatAssignments: ComputedRef<SeatAssignment[]>;
  sessionController: PlannerSessionController;
  draftLane: DraftLane;
  smartRuleLane: SmartRuleLane;
  smartRuleUiState: SmartRuleUiState;
};

export function createClassroomPlannerStateSupport(
  options: CreateClassroomPlannerStateSupportOptions,
) {
  function cloneRoster(nextRoster: Roster): Roster {
    return {
      ...nextRoster,
      students: nextRoster.students.map((student) => ({ ...student })),
    };
  }

  function cloneTemplate(nextTemplate: RoomTemplate): RoomTemplate {
    return {
      ...nextTemplate,
      seats: nextTemplate.seats.map((seat) => ({ ...seat })),
      fixtures: nextTemplate.fixtures.map((fixture) => ({ ...fixture })),
    };
  }

  function normalizeMutationError(error: unknown, fallbackMessage: string): string {
    if (isApiError(error)) {
      return error.message || fallbackMessage;
    }
    if (error instanceof Error && error.message) {
      return error.message;
    }
    return fallbackMessage;
  }

  function normalizeSeatingPreferencesCollection(
    preferences: StudentSeatingPreference[],
  ): StudentSeatingPreference[] {
    return preferences
      .filter((preference) => preference.near_teacher === true)
      .map((preference) => ({ ...preference }));
  }

  function clearRosterSmartRules(optionsArg: { resetUiState?: boolean } = {}): void {
    options.seatingPreferences.value = [];
    options.relationshipRules.value = [];
    options.smartRulesRevision.value = 0;
    if (optionsArg.resetUiState ?? true) {
      options.smartRuleUiState.reset();
      return;
    }
    options.smartRuleUiState.clearPendingRelationshipSelection();
  }

  function applyWorkspace(workspace: DraftWorkspaceResponse): void {
    options.draft.value = workspace.draft;
    options.roster.value = cloneRoster(workspace.roster);
    options.template.value = workspace.template ? cloneTemplate(workspace.template) : null;
    options.groups.value = reindexGroups(
      [...workspace.groups].sort((left, right) => left.sort_order - right.sort_order),
    );
    options.groupAssignmentsByStudentId.value = normalizeAssignments(
      workspace.group_assignments,
      "group_id",
    );
    options.seatAssignmentsByStudentId.value = normalizeAssignments(
      workspace.seat_assignments,
      "seat_id",
    );
    options.studentPlanningMetaByStudentId.value = Object.fromEntries(
      workspace.student_planning_meta.map((meta) => [meta.student_id, meta]),
    );
    options.historyStatus.value = workspace.history_status;
    options.historyActionInFlight.value = false;
  }

  function applyRosterSmartRules(rules: RosterSmartRulesResponse): void {
    options.seatingPreferences.value = normalizeSeatingPreferencesCollection(
      rules.seating_preferences,
    );
    options.relationshipRules.value = rules.relationship_rules.map((rule) => ({
      ...rule,
      student_ids: [...rule.student_ids],
    }));
    options.smartRulesRevision.value = rules.revision;
    options.smartRuleLane.applyHydratedRules();
  }

  function applyDraftSaveAcknowledgement(workspace: DraftWorkspaceResponse): void {
    if (!options.draft.value || options.draft.value.id !== workspace.draft.id) {
      return;
    }
    options.draft.value = {
      ...options.draft.value,
      revision: workspace.draft.revision,
      last_opened_at: workspace.draft.last_opened_at,
    };
    options.historyStatus.value = workspace.history_status;
    options.historyActionInFlight.value = false;
  }

  function applySmartRuleSaveAcknowledgement(rules: RosterSmartRulesResponse): void {
    if (!options.roster.value || options.roster.value.id !== rules.roster_id) {
      return;
    }
    options.smartRulesRevision.value = rules.revision;
    options.smartRuleLane.applyHydratedRules();
  }

  function replaceCurrentTemplate(nextTemplate: RoomTemplate): void {
    if (options.template.value?.id !== nextTemplate.id) {
      return;
    }

    const seatIds = new Set(nextTemplate.seats.map((seat) => seat.id));
    options.template.value = cloneTemplate(nextTemplate);
    options.seatAssignmentsByStudentId.value = Object.fromEntries(
      Object.entries(options.seatAssignmentsByStudentId.value).filter(([, seatId]) => {
        return typeof seatId === "string" && seatIds.has(seatId);
      }),
    );
  }

  function replaceCurrentRoster(nextRoster: Roster): void {
    if (options.roster.value?.id !== nextRoster.id) {
      return;
    }

    const studentIds = new Set(nextRoster.students.map((student) => student.id));
    options.roster.value = cloneRoster(nextRoster);
    options.groupAssignmentsByStudentId.value = Object.fromEntries(
      Object.entries(options.groupAssignmentsByStudentId.value).filter(([studentId]) => {
        return studentIds.has(studentId);
      }),
    );
    options.seatAssignmentsByStudentId.value = Object.fromEntries(
      Object.entries(options.seatAssignmentsByStudentId.value).filter(([studentId]) => {
        return studentIds.has(studentId);
      }),
    );
    options.studentPlanningMetaByStudentId.value = Object.fromEntries(
      Object.entries(options.studentPlanningMetaByStudentId.value).filter(([studentId]) => {
        return studentIds.has(studentId);
      }),
    );
    options.seatingPreferences.value = options.seatingPreferences.value.filter((preference) => {
      return studentIds.has(preference.student_id);
    });
    options.relationshipRules.value = options.relationshipRules.value
      .map((rule) => ({
        ...rule,
        student_ids: [...new Set(rule.student_ids.filter((studentId) => studentIds.has(studentId)))],
      }))
      .filter((rule) => rule.student_ids.length >= 2);
    options.smartRuleUiState.reset();
  }

  function serializeDraftPatch() {
    return {
      expected_revision: options.draft.value?.revision ?? null,
      smart_enabled: options.draft.value?.smart_enabled ?? false,
      use_history: options.draft.value?.use_history ?? false,
      groups: options.groups.value.map((group) => ({ ...group })),
      group_assignments: options.groupAssignments.value.map((assignment) => ({ ...assignment })),
      seat_assignments: options.seatAssignments.value.map((assignment) => ({ ...assignment })),
      student_planning_meta: options.studentPlanningMeta.value.map((meta) => ({ ...meta })),
    };
  }

  function serializeSmartRulesPatch() {
    return {
      expected_revision: options.smartRulesRevision.value,
      seating_preferences: normalizeSeatingPreferencesCollection(options.seatingPreferences.value),
      relationship_rules: options.relationshipRules.value.map((rule) => ({
        ...rule,
        student_ids: [...rule.student_ids],
      })),
    };
  }

  function createTransitionController() {
    return {
      draft: options.draft.value,
      flushDraftPersistenceLane: async () => {
        return await options.draftLane.flushPendingChanges();
      },
      flushSmartRuleLane: async () => {
        return await options.smartRuleLane.flushPendingChanges();
      },
      discardDraftPersistenceLane: (): void => {
        options.draftLane.discardPendingChanges();
      },
      discardSmartRuleLane: (): void => {
        options.smartRuleLane.discardPendingChanges();
      },
    };
  }

  function syncVisibleSessionBindings(): void {
    options.draftLane.syncBoundDraft(options.draft.value?.id ?? null);
    options.smartRuleLane.syncBoundRoster(options.roster.value?.id ?? null);
  }

  function discardPendingSessionWork(): void {
    options.sessionController.invalidateAsyncState();
    options.historyActionInFlight.value = false;
    discardPlannerSession(createTransitionController());
  }

  function clearWorkspace(): void {
    options.sessionController.clearSession();
    options.draftLane.resetBoundDraft(null);
    options.smartRuleLane.bindRoster(null);
    options.smartRuleUiState.reset();
    options.draft.value = null;
    options.roster.value = null;
    options.template.value = null;
    options.groups.value = [];
    options.groupAssignmentsByStudentId.value = {};
    options.seatAssignmentsByStudentId.value = {};
    options.studentPlanningMetaByStudentId.value = {};
    options.seatingPreferences.value = [];
    options.relationshipRules.value = [];
    options.smartRulesRevision.value = 0;
    options.historyStatus.value = {
      can_undo: false,
      can_redo: false,
    };
    options.historyActionInFlight.value = false;
  }

  return {
    normalizeMutationError,
    normalizeSeatingPreferencesCollection,
    clearRosterSmartRules,
    applyWorkspace,
    applyRosterSmartRules,
    applyDraftSaveAcknowledgement,
    applySmartRuleSaveAcknowledgement,
    replaceCurrentTemplate,
    replaceCurrentRoster,
    serializeDraftPatch,
    serializeSmartRulesPatch,
    createTransitionController,
    syncVisibleSessionBindings,
    discardPendingSessionWork,
    clearWorkspace,
  };
}
