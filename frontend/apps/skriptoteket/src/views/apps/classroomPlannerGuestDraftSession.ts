/**
 * Classroom planner guest draft/session controller.
 *
 * This module owns the browser-owned guest planner state used by public
 * Klassrumskartan checkpoint 3. It reuses the shipped planner mutation and
 * status helpers while keeping lifecycle, draft persistence, and smart-rule
 * hydration inside the guest snapshot boundary instead of the authenticated
 * API boundary.
 */

import { computed, ref } from "vue";

import { createPlannerStatusModel } from "./classroomPlannerStatus";
import {
  buildFixtureMap,
  buildGroupMap,
  buildSeatMap,
  buildStudentMap,
  createPlannerMutationActions,
} from "./classroomPlannerStoreMutations";
import { createClassroomPlannerSmartRuleActions } from "./classroomPlannerSmartRuleActions";
import { createClassroomPlannerStateSupport } from "./classroomPlannerStateSupport";
import {
  createClassroomPlannerGuestDraftPersistence,
  type CreateClassroomPlannerGuestDraftSessionOptions,
} from "./classroomPlannerGuestDraftPersistence";
import { createClassroomPlannerGuestDraftWorkspace } from "./classroomPlannerGuestDraftWorkspace";
import { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import { usePlannerSessionController } from "./usePlannerSessionController";
import { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";
import { useSmartRuleUiState } from "./useSmartRuleUiState";
import type {
  DraftGroup,
  GroupAssignment,
  PlanDraft,
  RelationshipRule,
  RoomTemplate,
  Roster,
  SeatAssignment,
  Student,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";

export function createClassroomPlannerGuestDraftSession(
  options: CreateClassroomPlannerGuestDraftSessionOptions,
) {
  const draft = ref<PlanDraft | null>(null);
  const roster = ref<Roster | null>(null);
  const template = ref<RoomTemplate | null>(null);
  const groups = ref<DraftGroup[]>([]);
  const groupAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const seatAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const seatingPreferences = ref<StudentSeatingPreference[]>([]);
  const relationshipRules = ref<RelationshipRule[]>([]);
  const smartRulesRevision = ref(0);
  const historyStatus = ref({
    can_undo: false,
    can_redo: false,
  });
  const historyActionInFlight = ref(false);
  const smartGroupingRunInFlight = ref(false);
  const smartSeatingRunInFlight = ref(false);

  const sessionController = usePlannerSessionController();

  const hasWorkspace = computed(() => draft.value !== null && roster.value !== null);
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

  const ungroupedStudents = computed<Student[]>(() => {
    return students.value.filter((student) => !groupAssignmentsByStudentId.value[student.id]);
  });

  const unseatedStudents = computed<Student[]>(() => {
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
      throw new Error("Guest planner state support has not been initialized.");
    }
    return stateSupportHolder.current;
  }
  const persistence = createClassroomPlannerGuestDraftPersistence({
    options,
    draft,
    roster,
    template,
    groups,
    groupAssignments,
    seatAssignments,
    seatingPreferences,
    relationshipRules,
    smartRulesRevision,
  });

  const draftLane = useDraftPersistenceLane({
    canSchedule: () => !isWorkspaceBusy.value,
    getSessionToken: () => sessionController.sessionToken.value,
    normalizeErrorMessage: (_error, fallbackMessage) => fallbackMessage,
    persistDraft: async () => await persistence.persistGuestWorkspace(),
    serializePatch: () => getStateSupport().serializeDraftPatch(),
    applyCommittedWorkspace: (workspace) => {
      getStateSupport().applyWorkspace(workspace);
    },
    applyAcknowledgement: (workspace) => {
      getStateSupport().applyDraftSaveAcknowledgement(workspace);
    },
  });

  const smartRuleLane = useRosterSmartRuleLane({
    canSchedule: () => !isWorkspaceBusy.value,
    getSessionToken: () => sessionController.sessionToken.value,
    normalizeErrorMessage: (_error, fallbackMessage) => fallbackMessage,
    persistSmartRules: async () => await persistence.persistGuestSmartRules(),
    serializePatch: () => getStateSupport().serializeSmartRulesPatch(),
    applyCommittedRules: (rules) => {
      getStateSupport().applyRosterSmartRules(rules);
    },
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

  const smartRuleActions = createClassroomPlannerSmartRuleActions({
    draft,
    seatingPreferences,
    relationshipRules,
    studentsById,
    isWorkspaceBusy,
    canEditSeatingSmartRules,
    draftLane,
    smartRuleLane,
    smartRuleUiState,
    syncVisibleSessionBindings: stateSupport.syncVisibleSessionBindings,
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
  const workspaceActions = createClassroomPlannerGuestDraftWorkspace({
    options,
    draft,
    roster,
    template,
    groups,
    groupAssignments,
    seatAssignments,
    sessionController,
    draftLane,
    smartRuleLane,
    stateSupport,
    persistence,
  });

  const smartGroupingRunMessage = ref<string | null>(null);
  const smartGroupingRunTone = ref<"neutral" | "success" | "warning">("neutral");
  const smartSeatingRunMessage = ref<string | null>(null);
  const smartSeatingRunTone = ref<"neutral" | "success" | "warning">("neutral");

  function clearGuestSmartRunFeedback(): void {
    smartGroupingRunMessage.value = null;
    smartGroupingRunTone.value = "neutral";
    smartSeatingRunMessage.value = null;
    smartSeatingRunTone.value = "neutral";
  }

  async function runGroupingShuffle(): Promise<void> {
    clearGuestSmartRunFeedback();
    mutationActions.randomizeGroups();
  }

  async function runSeatingShuffle(): Promise<void> {
    clearGuestSmartRunFeedback();
    mutationActions.randomizeSeating();
  }

  async function noopHistoryAction(): Promise<void> {
    return;
  }

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
    isRunningSmartGrouping: computed(() => smartGroupingRunInFlight.value),
    smartGroupingRunMessage,
    smartGroupingRunTone,
    isRunningSmartSeating: computed(() => smartSeatingRunInFlight.value),
    smartSeatingRunMessage,
    smartSeatingRunTone,
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
    smartRulesRevision,
    smartRulesHydrated,
    activeSeatingSmartTool: smartRuleUiState.activeSeatingSmartTool,
    pendingRelationshipStudentIds: smartRuleUiState.pendingRelationshipStudentIds,
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
    clearWorkspace: stateSupport.clearWorkspace,
    discardPendingSessionWork: stateSupport.discardPendingSessionWork,
    replaceCurrentRoster: stateSupport.replaceCurrentRoster,
    replaceCurrentTemplate: stateSupport.replaceCurrentTemplate,
    prepareForWorkspaceSwitch: workspaceActions.prepareForWorkspaceSwitch,
    prepareForExport: workspaceActions.prepareForExport,
    prepareForPlannerExit: workspaceActions.prepareForPlannerExit,
    retrySmartRuleHydration: workspaceActions.retrySmartRuleHydration,
    resolveDraft: workspaceActions.resolveDraft,
    startNewGroupingDraft: workspaceActions.startNewGroupingDraft,
    startNewSeatingDraft: workspaceActions.startNewSeatingDraft,
    loadWorkspace: workspaceActions.loadWorkspace,
    reloadActiveWorkspace: async () => {
      if (!draft.value) {
        return;
      }
      await workspaceActions.loadWorkspace(draft.value.id);
    },
    activateGroupingHistoryDraft: noopHistoryAction,
    deleteGroupingHistoryDraft: noopHistoryAction,
    activateSeatingHistoryDraft: noopHistoryAction,
    deleteSeatingHistoryDraft: noopHistoryAction,
    undoGroupingDraft: noopHistoryAction,
    redoGroupingDraft: noopHistoryAction,
    undoSeatingDraft: noopHistoryAction,
    redoSeatingDraft: noopHistoryAction,
    getResumableDraft: persistence.getResumableDraft,
    getClassWorkspaceSummary: persistence.getClassWorkspaceSummary,
    abandonDraft: async () => ({ status: "saved" as const }),
    setDraftSmartEnabled: smartRuleActions.setDraftSmartEnabled,
    setDraftUseHistoryEnabled: smartRuleActions.setDraftUseHistoryEnabled,
    setActiveSeatingSmartTool: smartRuleUiState.setActiveSeatingSmartTool,
    clearPendingRelationshipSelection: smartRuleUiState.clearPendingRelationshipSelection,
    setStudentNearTeacherEnabled: smartRuleActions.setStudentNearTeacherEnabled,
    replaceNearTeacherPreference: smartRuleActions.replaceNearTeacherPreference,
    handleSeatingSmartToolStudentSelection: smartRuleActions.handleSeatingSmartToolStudentSelection,
    commitPendingRelationshipRule: smartRuleActions.commitPendingRelationshipRule,
    beginRelationshipRuleEdit: smartRuleActions.beginRelationshipRuleEdit,
    beginNearTeacherEdit: smartRuleActions.beginNearTeacherEdit,
    clearNearTeacherRule: smartRuleActions.clearNearTeacherRule,
    deleteRelationshipRule: smartRuleActions.deleteRelationshipRule,
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
    runGroupingShuffle,
    randomizeSeating: mutationActions.randomizeSeating,
    runSeatingShuffle,
    persistCurrentWorkspaceToOverview: workspaceActions.persistCurrentWorkspaceToOverview,
    persistOverviewUiState: workspaceActions.persistOverviewUiState,
  };
}
