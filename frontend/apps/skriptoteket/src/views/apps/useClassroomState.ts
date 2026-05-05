/**
 * Classroom planner state adapter.
 *
 * Purpose:
 *   Compose the active Klassrumskartan planner session out of dedicated
 *   modules: one session controller, one draft persistence lane, one roster
 *   smart-rule lane, one smart-rule UI bucket, and explicit transition
 *   policies. This file intentionally stays a thin adapter over those
 *   contracts plus the shipped grouping/seating mutation helpers.
 *
 * Relationships:
 *   - delegates session identity to `usePlannerSessionController.ts`
 *   - delegates draft persistence to `useDraftPersistenceLane.ts`
 *   - delegates roster smart-rule state to `useRosterSmartRuleLane.ts`
 *   - delegates transient smart-rule UI state to `useSmartRuleUiState.ts`
 *   - delegates transition semantics to `plannerTransitionPolicies.ts`
 */

import {
  computed,
  inject,
  provide,
  ref,
  type InjectionKey,
} from "vue";
import { defineStore } from "pinia";

import { apiDelete, apiGet, apiPatch, apiPost } from "../../api/client";
import { createPlannerStatusModel } from "./classroomPlannerStatus";
import { createClassroomPlannerLifecycle } from "./classroomPlannerLifecycle";
import { createClassroomPlannerSmartRuleActions } from "./classroomPlannerSmartRuleActions";
import { createClassroomPlannerSmartRunActions } from "./classroomPlannerSmartRunActions";
import { createClassroomPlannerStateSupport } from "./classroomPlannerStateSupport";
import {
  buildFixtureMap,
  buildGroupMap,
  buildSeatMap,
  buildStudentMap,
  createPlannerMutationActions,
} from "./classroomPlannerStoreMutations";
import { useSmartGroupingRun } from "./useSmartGroupingRun";
import { useSmartSeatingRun } from "./useSmartSeatingRun";
import type {
  DraftGroup,
  DraftHistoryStatus,
  FixedSeatRule,
  GroupAssignment,
  PlanDraft,
  RelationshipRule,
  RoomTemplate,
  Roster,
  SeatAssignment,
  Student,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import { usePlannerSessionController } from "./usePlannerSessionController";
import { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";
import { useSmartRuleUiState } from "./useSmartRuleUiState";

const EXIT_AUTOSAVE_TIMEOUT_MS = 1500;
const SMART_RULE_HYDRATION_FALLBACK_MESSAGE = "Kunde inte ladda smarta regler.";

const useAuthenticatedClassroomStateStore = defineStore("classroom-state", () => {
  const draft = ref<PlanDraft | null>(null);
  const roster = ref<Roster | null>(null);
  const template = ref<RoomTemplate | null>(null);
  const groups = ref<DraftGroup[]>([]);
  const groupAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const seatAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const seatingPreferences = ref<StudentSeatingPreference[]>([]);
  const relationshipRules = ref<RelationshipRule[]>([]);
  const fixedSeatRules = ref<FixedSeatRule[]>([]);
  const smartRulesRevision = ref(0);
  const historyStatus = ref<DraftHistoryStatus>({
    can_undo: false,
    can_redo: false,
  });
  const historyActionInFlight = ref(false);
  const smartGroupingRunInFlight = ref(false);
  const smartSeatingRunInFlight = ref(false);

  const sessionController = usePlannerSessionController();

  const hasWorkspace = computed(() => {
    return draft.value !== null && roster.value !== null;
  });

  const isWorkspaceBusy = computed(() => {
    return (
      historyActionInFlight.value
      || smartGroupingRunInFlight.value
      || smartSeatingRunInFlight.value
      || sessionController.transitionDepth.value > 0
    );
  });

  const students = computed(() => roster.value?.students ?? []);
  const seats = computed(() => template.value?.seats ?? []);
  const fixtures = computed(() => template.value?.fixtures ?? []);

  const studentsById = computed(() => buildStudentMap(students.value));
  const seatsById = computed(() => buildSeatMap(seats.value));
  const fixturesById = computed(() => buildFixtureMap(fixtures.value));
  const groupsById = computed(() => buildGroupMap(groups.value));
  const hasAssignedTarget = (
    entry: [string, string | null],
  ): entry is [string, string] => {
    return typeof entry[1] === "string" && entry[1].length > 0;
  };

  const groupAssignments = computed<GroupAssignment[]>(() => {
    return Object.entries(groupAssignmentsByStudentId.value)
      .filter(hasAssignedTarget)
      .map(([studentId, groupId]) => ({ student_id: studentId, group_id: groupId }));
  });

  const seatAssignments = computed<SeatAssignment[]>(() => {
    return Object.entries(seatAssignmentsByStudentId.value)
      .filter(hasAssignedTarget)
      .map(([studentId, seatId]) => ({ student_id: studentId, seat_id: seatId }));
  });

  const ungroupedStudents = computed(() => {
    return students.value.filter((student) => !groupAssignmentsByStudentId.value[student.id]);
  });

  const unseatedStudents = computed(() => {
    return students.value.filter((student) => !seatAssignmentsByStudentId.value[student.id]);
  });

  const studentsByGroupId = computed<Record<string, Student[]>>(() => {
    const grouped: Record<string, Student[]> = {};
    for (const group of groups.value) {
      grouped[group.id] = [];
    }
    for (const student of students.value) {
      const groupId = groupAssignmentsByStudentId.value[student.id];
      if (groupId && grouped[groupId]) {
        grouped[groupId].push(student);
      }
    }
    return grouped;
  });

  const studentBySeatId = computed<Record<string, Student | null>>(() => {
    const placed: Record<string, Student | null> = {};
    for (const seat of seats.value) {
      placed[seat.id] = null;
    }
    for (const student of students.value) {
      const seatId = seatAssignmentsByStudentId.value[student.id];
      if (seatId && placed[seatId] !== undefined) {
        placed[seatId] = student;
      }
    }
    return placed;
  });

  const zones = computed(() => {
    return Array.from(
      new Set(
        seats.value
          .map((seat) => seat.zone ?? null)
          .filter((zone): zone is string => typeof zone === "string" && zone.length > 0),
      ),
    ).sort();
  });

  const smartRuleUiState = useSmartRuleUiState({
    canEditSmartRules: () => canEditSeatingSmartRules.value,
  });

  const stateSupportHolder: {
    current: ReturnType<typeof createClassroomPlannerStateSupport> | null;
  } = { current: null };

  function getStateSupport(): ReturnType<typeof createClassroomPlannerStateSupport> {
    if (!stateSupportHolder.current) {
      throw new Error("Planner state support has not been initialized.");
    }
    return stateSupportHolder.current;
  }

  const draftLane = useDraftPersistenceLane({
    canSchedule: () => !isWorkspaceBusy.value,
    getSessionToken: () => sessionController.sessionToken.value,
    normalizeErrorMessage: (error, fallbackMessage) => {
      return getStateSupport().normalizeMutationError(error, fallbackMessage);
    },
    persistDraft: async (draftId, patch) => {
      return await apiPatch(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draftId}`,
        patch,
      );
    },
    serializePatch: () => getStateSupport().serializeDraftPatch(),
    applyCommittedWorkspace: (workspace) => getStateSupport().applyWorkspace(workspace),
    applyAcknowledgement: (workspace) => {
      getStateSupport().applyDraftSaveAcknowledgement(workspace);
    },
  });

  const smartRuleLane = useRosterSmartRuleLane({
    canSchedule: () => !isWorkspaceBusy.value,
    getSessionToken: () => sessionController.sessionToken.value,
    normalizeErrorMessage: (error, fallbackMessage) => {
      return getStateSupport().normalizeMutationError(error, fallbackMessage);
    },
    persistSmartRules: async (rosterId, patch) => {
      return await apiPatch(
        `/api/v1/apps/classroom.group-seating-studio/rosters/${rosterId}/smart-rules`,
        patch,
      );
    },
    serializePatch: () => getStateSupport().serializeSmartRulesPatch(),
    applyCommittedRules: (rules) => getStateSupport().applyRosterSmartRules(rules),
    applyAcknowledgement: (rules) => {
      getStateSupport().applySmartRuleSaveAcknowledgement(rules);
    },
  });

  const hasPendingAutosave = computed(() => {
    return draftLane.hasPendingChanges.value || smartRuleLane.hasPendingChanges.value;
  });

  const smartRulesHydrated = computed(() => smartRuleLane.isHydrated.value);

  const canEditSeatingSmartRules = computed(() => {
    return roster.value !== null && smartRuleLane.isHydrated.value && !isWorkspaceBusy.value;
  });

  const canUndo = computed(() => {
    return (
      draft.value !== null
      && !isWorkspaceBusy.value
      && (historyStatus.value.can_undo || draftLane.hasPendingChanges.value)
    );
  });

  const canRedo = computed(() => {
    return draft.value !== null && !isWorkspaceBusy.value && historyStatus.value.can_redo;
  });

  stateSupportHolder.current = createClassroomPlannerStateSupport({
    draft,
    roster,
    template,
    groups,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    seatingPreferences,
    relationshipRules,
    fixedSeatRules,
    smartRulesRevision,
    historyStatus,
    historyActionInFlight,
    groupAssignments,
    seatAssignments,
    sessionController,
    draftLane,
    smartRuleLane,
    smartRuleUiState,
  });
  const stateSupport = getStateSupport();

  const plannerStatus = createPlannerStatusModel({
    draftPersistenceStatus: draftLane.status,
    draftPersistenceMessage: draftLane.message,
    draftIsSaving: draftLane.isSaving,
    smartRulePersistenceStatus: smartRuleLane.status,
    smartRulePersistenceMessage: smartRuleLane.message,
    smartRuleHydrationStatus: smartRuleLane.hydrationStatus,
    smartRuleHydrationMessage: smartRuleLane.hydrationMessage,
    smartRuleIsSaving: smartRuleLane.isSaving,
    hasPendingAutosave,
    isWorkspaceBusy,
  });

  const smartSeatingRun = useSmartSeatingRun({
    draft,
    smartRulesHydrated,
    runningState: smartSeatingRunInFlight,
    flushDraftLane: draftLane.flushPendingChanges,
    flushSmartRuleLane: smartRuleLane.flushPendingChanges,
    applyWorkspace: stateSupport.applyWorkspace,
    normalizeErrorMessage: stateSupport.normalizeMutationError,
  });
  const smartGroupingRun = useSmartGroupingRun({
    draft,
    smartRulesHydrated,
    runningState: smartGroupingRunInFlight,
    flushDraftLane: draftLane.flushPendingChanges,
    flushSmartRuleLane: smartRuleLane.flushPendingChanges,
    applyWorkspace: stateSupport.applyWorkspace,
    normalizeErrorMessage: stateSupport.normalizeMutationError,
  });

  const smartRuleActions = createClassroomPlannerSmartRuleActions({
    draft,
    template,
    seatingPreferences,
    relationshipRules,
    fixedSeatRules,
    studentsById,
    seatsById,
    isWorkspaceBusy,
    canEditSeatingSmartRules,
    draftLane,
    smartRuleLane,
    smartRuleUiState,
    syncVisibleSessionBindings: stateSupport.syncVisibleSessionBindings,
  });

  const lifecycle = createClassroomPlannerLifecycle({
    apiDelete,
    apiGet,
    apiPost,
    exitAutosaveTimeoutMs: EXIT_AUTOSAVE_TIMEOUT_MS,
    smartRuleHydrationFallbackMessage: SMART_RULE_HYDRATION_FALLBACK_MESSAGE,
    draft,
    roster,
    historyActionInFlight,
    sessionController,
    syncVisibleSessionBindings: stateSupport.syncVisibleSessionBindings,
    createTransitionController: stateSupport.createTransitionController,
    normalizeMutationError: stateSupport.normalizeMutationError,
    clearRosterSmartRules: stateSupport.clearRosterSmartRules,
    applyWorkspace: stateSupport.applyWorkspace,
    applyRosterSmartRules: stateSupport.applyRosterSmartRules,
    clearWorkspace: stateSupport.clearWorkspace,
    discardPendingSessionWork: stateSupport.discardPendingSessionWork,
    discardPendingDraftChanges: draftLane.discardPendingChanges,
    resetBoundDraft: draftLane.resetBoundDraft,
    bindSmartRuleRoster: smartRuleLane.bindRoster,
    markSmartRuleHydrating: smartRuleLane.markHydrating,
    failSmartRuleHydration: smartRuleLane.failHydration,
  });

  const mutationActions = createPlannerMutationActions({
    students,
    studentsById,
    seatsById,
    groupsById,
    groups,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    canMutate: () => !isWorkspaceBusy.value,
    markDirty: () => {
      stateSupport.syncVisibleSessionBindings();
      draftLane.markDirty();
    },
  });

  const smartRunActions = createClassroomPlannerSmartRunActions({
    draft,
    smartSeatingRun,
    smartGroupingRun,
    randomizeSeating: mutationActions.randomizeSeating,
    randomizeGroups: mutationActions.randomizeGroups,
  });

  return {
    draft,
    roster,
    template,
    groups,
    historyStatus,
    draftPersistenceStatus: draftLane.status,
    draftPersistenceMessage: draftLane.message,
    smartRulePersistenceStatus: smartRuleLane.status,
    smartRulePersistenceMessage: smartRuleLane.message,
    smartRuleHydrationStatus: smartRuleLane.hydrationStatus,
    smartRuleHydrationMessage: smartRuleLane.hydrationMessage,
    isRunningSmartGrouping: smartGroupingRun.isBusy,
    smartGroupingRunMessage: smartGroupingRun.message,
    smartGroupingRunTone: smartGroupingRun.tone,
    isRunningSmartSeating: smartSeatingRun.isBusy,
    smartSeatingRunMessage: smartSeatingRun.message,
    smartSeatingRunTone: smartSeatingRun.tone,
    plannerStatusLabel: plannerStatus.plannerStatusLabel,
    plannerStatusMessage: plannerStatus.plannerStatusMessage,
    plannerStatusTone: plannerStatus.plannerStatusTone,
    plannerConflictMessage: plannerStatus.plannerConflictMessage,
    isWorkspaceBusy,
    canEditSeatingSmartRules,
    hasPendingAutosave,
    hasWorkspace,
    students,
    seats,
    fixtures,
    studentsById,
    seatsById,
    fixturesById,
    groupsById,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    seatingPreferences,
    relationshipRules,
    fixedSeatRules,
    smartRulesRevision,
    smartRulesHydrated,
    activeSeatingSmartTool: smartRuleUiState.activeSeatingSmartTool,
    pendingRelationshipStudentIds: smartRuleUiState.pendingRelationshipStudentIds,
    pendingFixedSeatStudentId: smartRuleUiState.pendingFixedSeatStudentId,
    pendingFixedSeatSeatId: smartRuleUiState.pendingFixedSeatSeatId,
    editingFixedSeatRuleId: smartRuleUiState.editingFixedSeatRuleId,
    editingRelationshipRuleId: smartRuleUiState.editingRelationshipRuleId,
    editingNearTeacherRule: smartRuleUiState.editingNearTeacherRule,
    smartRuleFeedbackMessage: smartRuleUiState.feedbackMessage,
    groupAssignments,
    seatAssignments,
    ungroupedStudents,
    unseatedStudents,
    studentsByGroupId,
    studentBySeatId,
    zones,
    canUndo,
    canRedo,
    canCommitPendingRelationshipRule: smartRuleUiState.canCommitPendingRelationshipRule,
    canCommitPendingFixedSeatRule: smartRuleUiState.canCommitPendingFixedSeatRule,
    clearWorkspace: stateSupport.clearWorkspace,
    discardPendingSessionWork: stateSupport.discardPendingSessionWork,
    replaceCurrentRoster: stateSupport.replaceCurrentRoster,
    replaceCurrentTemplate: stateSupport.replaceCurrentTemplate,
    prepareForWorkspaceSwitch: lifecycle.prepareForWorkspaceSwitch,
    prepareForExport: lifecycle.prepareForExport,
    prepareForPlannerExit: lifecycle.prepareForPlannerExit,
    retrySmartRuleHydration: lifecycle.retrySmartRuleHydration,
    resolveDraft: lifecycle.resolveDraft,
    startNewGroupingDraft: lifecycle.startNewGroupingDraft,
    startNewSeatingDraft: lifecycle.startNewSeatingDraft,
    loadWorkspace: lifecycle.loadWorkspace,
    reloadActiveWorkspace: lifecycle.reloadActiveWorkspace,
    activateGroupingHistoryDraft: lifecycle.activateGroupingHistoryDraft,
    deleteGroupingHistoryDraft: lifecycle.deleteGroupingHistoryDraft,
    activateSeatingHistoryDraft: lifecycle.activateSeatingHistoryDraft,
    deleteSeatingHistoryDraft: lifecycle.deleteSeatingHistoryDraft,
    undoGroupingDraft: lifecycle.undoGroupingDraft,
    redoGroupingDraft: lifecycle.redoGroupingDraft,
    undoSeatingDraft: lifecycle.undoSeatingDraft,
    redoSeatingDraft: lifecycle.redoSeatingDraft,
    getResumableDraft: lifecycle.getResumableDraft,
    getClassWorkspaceSummary: lifecycle.getClassWorkspaceSummary,
    abandonDraft: lifecycle.abandonDraft,
    setDraftSmartEnabled: smartRuleActions.setDraftSmartEnabled,
    setDraftUseHistoryEnabled: smartRuleActions.setDraftUseHistoryEnabled,
    setActiveSeatingSmartTool: smartRuleUiState.setActiveSeatingSmartTool,
    clearPendingRelationshipSelection: smartRuleUiState.clearPendingRelationshipSelection,
    setStudentNearTeacherEnabled: smartRuleActions.setStudentNearTeacherEnabled,
    replaceNearTeacherPreference: smartRuleActions.replaceNearTeacherPreference,
    handleSeatingSmartToolStudentSelection: smartRuleActions.handleSeatingSmartToolStudentSelection,
    commitPendingRelationshipRule: smartRuleActions.commitPendingRelationshipRule,
    selectFixedSeatRuleSeat: smartRuleActions.selectFixedSeatRuleSeat,
    commitPendingFixedSeatRule: smartRuleActions.commitPendingFixedSeatRule,
    beginRelationshipRuleEdit: smartRuleActions.beginRelationshipRuleEdit,
    beginNearTeacherEdit: smartRuleActions.beginNearTeacherEdit,
    beginFixedSeatRuleEdit: smartRuleActions.beginFixedSeatRuleEdit,
    clearNearTeacherRule: smartRuleActions.clearNearTeacherRule,
    deleteRelationshipRule: smartRuleActions.deleteRelationshipRule,
    deleteFixedSeatRule: smartRuleActions.deleteFixedSeatRule,
    fixedSeatRuleForStudent: smartRuleActions.fixedSeatRuleForStudent,
    fixedSeatRuleForSeat: smartRuleActions.fixedSeatRuleForSeat,
    isStudentMarkedNearTeacher: smartRuleActions.isStudentMarkedNearTeacher,
    setDraftGroupingSeatingDistanceEnabled:
      smartRuleActions.setDraftGroupingSeatingDistanceEnabled,
    isStudentInPendingRelationshipSelection:
      smartRuleUiState.isStudentInPendingRelationshipSelection,
    assignStudentToGroup: mutationActions.assignStudentToGroup,
    removeStudentFromGroup: mutationActions.removeStudentFromGroup,
    clearGroupingAssignments: mutationActions.clearGroupingAssignments,
    assignStudentToSeat: mutationActions.assignStudentToSeat,
    swapSeatAssignments: mutationActions.swapSeatAssignments,
    clearSeatAssignment: mutationActions.clearSeatAssignment,
    clearSeatingAssignments: mutationActions.clearSeatingAssignments,
    addGroup: mutationActions.addGroup,
    renameGroup: mutationActions.renameGroup,
    moveGroup: mutationActions.moveGroup,
    removeGroup: mutationActions.removeGroup,
    randomizeGroups: mutationActions.randomizeGroups,
    runGroupingShuffle: smartRunActions.runGroupingShuffle,
    randomizeSeating: mutationActions.randomizeSeating,
    runSeatingShuffle: smartRunActions.runSeatingShuffle,
  };
});

export type ClassroomStateLike = ReturnType<typeof useAuthenticatedClassroomStateStore>;

const CLASSROOM_STATE_INJECTION_KEY: InjectionKey<ClassroomStateLike> =
  Symbol("classroom-state");

export function provideClassroomState(state: ClassroomStateLike): void {
  provide(CLASSROOM_STATE_INJECTION_KEY, state);
}

export function useClassroomState(): ClassroomStateLike {
  return inject(CLASSROOM_STATE_INJECTION_KEY, null) ?? useAuthenticatedClassroomStateStore();
}
