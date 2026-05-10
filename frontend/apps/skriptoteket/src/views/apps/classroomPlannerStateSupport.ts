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
import {
  normalizeClassroomPlannerRoster,
  normalizeClassroomPlannerSmartRules,
  normalizeClassroomPlannerTemplate,
  normalizeClassroomPlannerWorkspace,
} from "./classroomPlannerPayloadNormalization";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import {
  isGroupingSeatingDistanceEnabledByDefault,
  isHistoryEnabledByDefault,
  isSmartEnabledByDefault,
} from "./classroomPlannerSmartPreferences";
import type {
  DraftHistoryStatus,
  DraftGroup,
  FixedSeatRule,
  DraftWorkspaceResponse,
  GroupAssignment,
  PlanDraft,
  RelationshipRule,
  RoomTemplate,
  Roster,
  RosterSmartRulesResponse,
  SeatAssignment,
  SmartRuleDiagnostic,
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
  seatingPreferences: Ref<StudentSeatingPreference[]>;
  relationshipRules: Ref<RelationshipRule[]>;
  fixedSeatRules: Ref<FixedSeatRule[]>;
  smartRulesRevision: Ref<number>;
  historyStatus: Ref<DraftHistoryStatus>;
  historyActionInFlight: Ref<boolean>;
  groupAssignments: ComputedRef<GroupAssignment[]>;
  seatAssignments: ComputedRef<SeatAssignment[]>;
  sessionController: PlannerSessionController;
  draftLane: DraftLane;
  smartRuleLane: SmartRuleLane;
  smartRuleUiState: SmartRuleUiState;
  applyRuleDiagnostics?: (diagnostics: SmartRuleDiagnostic[]) => void;
  clearRuleDiagnostics?: () => void;
};

export function createClassroomPlannerStateSupport(
  options: CreateClassroomPlannerStateSupportOptions,
) {
  function cloneRoster(nextRoster: Roster): Roster {
    return normalizeClassroomPlannerRoster(nextRoster);
  }

  function cloneTemplate(nextTemplate: RoomTemplate): RoomTemplate {
    return normalizeClassroomPlannerTemplate(nextTemplate);
  }

  function normalizeMutationError(error: unknown, fallbackMessage: string): string {
    if (isApiError(error)) {
      return error.message || fallbackMessage;
    }
    return normalizeClassroomPlannerUiError(error, fallbackMessage);
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
    options.fixedSeatRules.value = [];
    options.smartRulesRevision.value = 0;
    if (optionsArg.resetUiState ?? true) {
      options.smartRuleUiState.reset();
      return;
    }
    options.smartRuleUiState.clearPendingRelationshipSelection();
  }

  function applyWorkspace(workspace: DraftWorkspaceResponse): void {
    const normalizedWorkspace = normalizeClassroomPlannerWorkspace(workspace);

    options.draft.value = normalizedWorkspace.draft;
    options.roster.value = normalizedWorkspace.roster;
    options.template.value = normalizedWorkspace.template ?? null;
    options.groups.value = reindexGroups(
      [...normalizedWorkspace.groups].sort((left, right) => left.sort_order - right.sort_order),
    );
    options.groupAssignmentsByStudentId.value = normalizeAssignments(
      normalizedWorkspace.group_assignments,
      "group_id",
    );
    options.seatAssignmentsByStudentId.value = normalizeAssignments(
      normalizedWorkspace.seat_assignments,
      "seat_id",
    );
    options.historyStatus.value = normalizedWorkspace.history_status;
    options.historyActionInFlight.value = false;
    options.applyRuleDiagnostics?.(normalizedWorkspace.rule_diagnostics ?? []);
  }

  function applyRosterSmartRules(rules: RosterSmartRulesResponse): void {
    const normalizedRules = normalizeClassroomPlannerSmartRules(rules);

    options.seatingPreferences.value = normalizeSeatingPreferencesCollection(
      normalizedRules.seating_preferences,
    );
    options.relationshipRules.value = normalizedRules.relationship_rules.map((rule) => ({
      ...rule,
      student_ids: [...rule.student_ids],
    }));
    options.fixedSeatRules.value = normalizedRules.fixed_seat_rules?.map((rule) => ({ ...rule })) ?? [];
    options.smartRulesRevision.value = normalizedRules.revision;
    options.smartRuleLane.applyHydratedRules();
  }

  function applyDraftSaveAcknowledgement(workspace: DraftWorkspaceResponse): void {
    const normalizedWorkspace = normalizeClassroomPlannerWorkspace(workspace);

    if (!options.draft.value || options.draft.value.id !== normalizedWorkspace.draft.id) {
      return;
    }
    options.draft.value = {
      ...options.draft.value,
      revision: normalizedWorkspace.draft.revision,
      last_opened_at: normalizedWorkspace.draft.last_opened_at,
    };
    options.historyStatus.value = normalizedWorkspace.history_status;
    options.historyActionInFlight.value = false;
    options.applyRuleDiagnostics?.(normalizedWorkspace.rule_diagnostics ?? []);
  }

  function applySmartRuleSaveAcknowledgement(rules: RosterSmartRulesResponse): void {
    if (!options.roster.value || options.roster.value.id !== rules.roster_id) {
      return;
    }
    options.smartRulesRevision.value = rules.revision;
    options.smartRuleLane.applyHydratedRules();
  }

  function replaceCurrentTemplate(nextTemplate: RoomTemplate): void {
    const normalizedTemplate = cloneTemplate(nextTemplate);

    if (options.template.value?.id !== normalizedTemplate.id) {
      return;
    }

    const seatIds = new Set(normalizedTemplate.seats.map((seat) => seat.id));
    options.template.value = normalizedTemplate;
    options.seatAssignmentsByStudentId.value = Object.fromEntries(
      Object.entries(options.seatAssignmentsByStudentId.value).filter(([, seatId]) => {
        return typeof seatId === "string" && seatIds.has(seatId);
      }),
    );
    options.fixedSeatRules.value = options.fixedSeatRules.value.filter((rule) => {
      return rule.template_id === normalizedTemplate.id && seatIds.has(rule.seat_id);
    });
    options.clearRuleDiagnostics?.();
  }

  function replaceCurrentRoster(nextRoster: Roster): void {
    const normalizedRoster = cloneRoster(nextRoster);

    if (options.roster.value?.id !== normalizedRoster.id) {
      return;
    }

    const studentIds = new Set(normalizedRoster.students.map((student) => student.id));
    options.roster.value = normalizedRoster;
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
    options.seatingPreferences.value = options.seatingPreferences.value.filter((preference) => {
      return studentIds.has(preference.student_id);
    });
    options.relationshipRules.value = options.relationshipRules.value
      .map((rule) => ({
        ...rule,
        student_ids: [...new Set(rule.student_ids.filter((studentId) => studentIds.has(studentId)))],
      }))
      .filter((rule) => rule.student_ids.length >= 2);
    options.fixedSeatRules.value = options.fixedSeatRules.value.filter((rule) => {
      return studentIds.has(rule.student_id);
    });
    options.smartRuleUiState.reset();
    options.clearRuleDiagnostics?.();
  }

  function serializeDraftPatch() {
    return {
      expected_revision: options.draft.value?.revision ?? null,
      smart_enabled: isSmartEnabledByDefault(options.draft.value),
      use_history: isHistoryEnabledByDefault(options.draft.value),
      grouping_seating_distance_enabled:
        isGroupingSeatingDistanceEnabledByDefault(options.draft.value),
      groups: options.groups.value.map((group) => ({ ...group })),
      group_assignments: options.groupAssignments.value.map((assignment) => ({ ...assignment })),
      seat_assignments: options.seatAssignments.value.map((assignment) => ({ ...assignment })),
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
      fixed_seat_rules: options.fixedSeatRules.value.map((rule) => ({ ...rule })),
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
    options.seatingPreferences.value = [];
    options.relationshipRules.value = [];
    options.fixedSeatRules.value = [];
    options.smartRulesRevision.value = 0;
    options.historyStatus.value = {
      can_undo: false,
      can_redo: false,
    };
    options.historyActionInFlight.value = false;
    options.clearRuleDiagnostics?.();
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
