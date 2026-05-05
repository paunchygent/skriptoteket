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
import { buildGuestWorkspaceResponse } from "./classroomPlannerGuestDraftMutations";
import { createPlannerMutationActions } from "./classroomPlannerStoreMutations";
import { createClassroomPlannerGuestDraftDerivedState } from "./classroomPlannerGuestDraftDerivedState";
import { createClassroomPlannerSmartRuleActions } from "./classroomPlannerSmartRuleActions";
import { createClassroomPlannerStateSupport } from "./classroomPlannerStateSupport";
import { createClassroomPlannerGuestDraftHistory } from "./classroomPlannerGuestDraftHistory";
import { createClassroomPlannerGuestDraftSessionApi } from "./classroomPlannerGuestDraftSessionApi";
import {
  PUBLIC_GROUPING_SMART_RUN_API_PATH,
  PUBLIC_SEATING_SMART_RUN_API_PATH,
} from "./classroomPlannerGuestControllerSupport";
import {
  createClassroomPlannerGuestDraftPersistence,
  type CreateClassroomPlannerGuestDraftSessionOptions,
} from "./classroomPlannerGuestDraftPersistence";
import { createClassroomPlannerGuestDraftWorkspace } from "./classroomPlannerGuestDraftWorkspace";
import { createClassroomPlannerSmartRunActions } from "./classroomPlannerSmartRunActions";
import { usePublicSmartGroupingRun } from "./usePublicSmartGroupingRun";
import { usePublicSmartSeatingRun } from "./usePublicSmartSeatingRun";
import { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import { usePlannerSessionController } from "./usePlannerSessionController";
import { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";
import { useSmartRuleUiState } from "./useSmartRuleUiState";
import type {
  DraftGroup,
  DraftWorkspaceResponse,
  FixedSeatRule,
  PlanDraft,
  RelationshipRule,
  RoomTemplate,
  Roster,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";

export function createClassroomPlannerGuestDraftSession(options: CreateClassroomPlannerGuestDraftSessionOptions) {
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
  const historyStatus = ref({
    can_undo: false,
    can_redo: false,
  });
  const historyActionInFlight = ref(false);
  const smartGroupingRunInFlight = ref(false);
  const smartSeatingRunInFlight = ref(false);
  const guestHistory = createClassroomPlannerGuestDraftHistory();
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
  const {
    students,
    seats,
    fixtures,
    studentsById,
    seatsById,
    fixturesById,
    groupsById,
    groupAssignments,
    seatAssignments,
    ungroupedStudents,
    unseatedStudents,
    studentsByGroupId,
    studentBySeatId,
    zones,
  } = createClassroomPlannerGuestDraftDerivedState({
    roster,
    template,
    groups,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
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
    fixedSeatRules,
    smartRulesRevision,
  });
  const draftLane = useDraftPersistenceLane({
    canSchedule: () => !isWorkspaceBusy.value,
    getSessionToken: () => sessionController.sessionToken.value,
    normalizeErrorMessage: (_error, fallbackMessage) => fallbackMessage,
    persistDraft: async () => await persistence.persistGuestWorkspace(),
    serializePatch: () => getStateSupport().serializeDraftPatch(),
    applyCommittedWorkspace: applyCommittedGuestWorkspace,
    applyAcknowledgement: applyGuestDraftSaveAcknowledgement,
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
    return draft.value !== null && !isWorkspaceBusy.value && historyStatus.value.can_undo;
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
  function syncGuestHistoryStatus(): void {
    historyStatus.value = guestHistory.getHistoryStatus(draft.value?.id ?? null);
  }
  function syncWorkspaceHistory(workspace: DraftWorkspaceResponse): void {
    guestHistory.bindWorkspace(workspace);
    syncGuestHistoryStatus();
  }
  function replaceCurrentGuestHistoryWorkspace(): void {
    const workspace = getCurrentWorkspace();
    if (!workspace) {
      syncGuestHistoryStatus();
      return;
    }
    guestHistory.replaceCurrentWorkspace(workspace);
    syncGuestHistoryStatus();
  }
  function captureCurrentGuestWorkspace(): void {
    const workspace = getCurrentWorkspace();
    if (!workspace) {
      syncGuestHistoryStatus();
      return;
    }
    guestHistory.captureWorkspace(workspace);
    syncGuestHistoryStatus();
  }
  function applyWorkspaceWithHistoryCapture(workspace: DraftWorkspaceResponse): void {
    stateSupport.applyWorkspace(workspace);
    captureCurrentGuestWorkspace();
  }
  function applyCommittedGuestWorkspace(workspace: DraftWorkspaceResponse): void {
    stateSupport.applyWorkspace(workspace);
    replaceCurrentGuestHistoryWorkspace();
  }
  function applyGuestDraftSaveAcknowledgement(workspace: DraftWorkspaceResponse): void {
    stateSupport.applyDraftSaveAcknowledgement(workspace);
    replaceCurrentGuestHistoryWorkspace();
  }
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
    onDraftMutation: captureCurrentGuestWorkspace,
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
      captureCurrentGuestWorkspace();
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
    syncWorkspaceHistory,
  });
  function getCurrentWorkspace() {
    if (!draft.value || !roster.value) {
      return null;
    }

    return buildGuestWorkspaceResponse({
      draft: draft.value,
      roster: roster.value,
      template: template.value,
      groups: groups.value,
      groupAssignments: groupAssignments.value,
      seatAssignments: seatAssignments.value,
    });
  }
  async function commitWorkspaceToSnapshot(workspace: DraftWorkspaceResponse) {
    stateSupport.syncVisibleSessionBindings();
    return await workspaceActions.commitWorkspaceToGuestSnapshot(workspace);
  }
  const publicSmartGroupingRun = usePublicSmartGroupingRun({
    apiPath: PUBLIC_GROUPING_SMART_RUN_API_PATH,
    draft,
    smartRulesHydrated,
    runningState: smartGroupingRunInFlight,
    flushDraftLane: draftLane.flushPendingChanges,
    flushSmartRuleLane: smartRuleLane.flushPendingChanges,
    getCurrentWorkspace,
    commitWorkspaceToSnapshot,
    applyWorkspace: applyWorkspaceWithHistoryCapture,
    normalizeErrorMessage: stateSupport.normalizeMutationError,
  });
  const publicSmartSeatingRun = usePublicSmartSeatingRun({
    apiPath: PUBLIC_SEATING_SMART_RUN_API_PATH,
    draft,
    smartRulesHydrated,
    runningState: smartSeatingRunInFlight,
    flushDraftLane: draftLane.flushPendingChanges,
    flushSmartRuleLane: smartRuleLane.flushPendingChanges,
    getCurrentWorkspace,
    commitWorkspaceToSnapshot,
    applyWorkspace: applyWorkspaceWithHistoryCapture,
    normalizeErrorMessage: stateSupport.normalizeMutationError,
  });
  const smartRunActions = createClassroomPlannerSmartRunActions({
    draft,
    smartSeatingRun: publicSmartSeatingRun,
    smartGroupingRun: publicSmartGroupingRun,
    randomizeSeating: mutationActions.randomizeSeating,
    randomizeGroups: mutationActions.randomizeGroups,
    clearFeedbackBeforeRun: true,
  });
  async function noopHistoryAction(): Promise<void> {
    return;
  }
  function buildHistoryWorkspace(
    workspace: DraftWorkspaceResponse,
  ): DraftWorkspaceResponse {
    return {
      ...workspace,
      draft: {
        ...workspace.draft,
        revision: draft.value?.revision ?? workspace.draft.revision,
        last_opened_at: draft.value?.last_opened_at ?? workspace.draft.last_opened_at,
      },
    };
  }
  async function applyGuestHistoryAction(direction: "undo" | "redo"): Promise<void> {
    if (!draft.value || isWorkspaceBusy.value) {
      return;
    }

    historyActionInFlight.value = true;
    try {
      const historyWorkspace = direction === "undo"
        ? guestHistory.undo(draft.value.id)
        : guestHistory.redo(draft.value.id);
      if (!historyWorkspace) {
        syncGuestHistoryStatus();
        return;
      }

      stateSupport.applyWorkspace(buildHistoryWorkspace(historyWorkspace));
      replaceCurrentGuestHistoryWorkspace();
      stateSupport.syncVisibleSessionBindings();
      draftLane.markDirty();
    } finally {
      historyActionInFlight.value = false;
    }
  }
  const reloadActiveWorkspace = async () => {
    if (!draft.value) {
      return;
    }
    await workspaceActions.loadWorkspace(draft.value.id);
  };

  function createScopedHistoryAction(
    draftKind: "grouping" | "seating",
    direction: "undo" | "redo",
  ) {
    return async () => {
      if (draft.value?.draft_kind !== draftKind) {
        return;
      }
      await applyGuestHistoryAction(direction);
    };
  }
  const undoGroupingDraft = createScopedHistoryAction("grouping", "undo");
  const redoGroupingDraft = createScopedHistoryAction("grouping", "redo");
  const undoSeatingDraft = createScopedHistoryAction("seating", "undo");
  const redoSeatingDraft = createScopedHistoryAction("seating", "redo");
  const abandonDraft = async () => ({ status: "saved" as const });
  return createClassroomPlannerGuestDraftSessionApi({
    sessionState: {
      draft, roster, template, groups, historyStatus,
      draftPersistenceStatus: draftLane.status,
      draftPersistenceMessage: draftLane.message,
      smartRulePersistenceStatus: smartRuleLane.status,
      smartRulePersistenceMessage: smartRuleLane.message,
      smartRuleHydrationStatus: smartRuleLane.hydrationStatus,
      smartRuleHydrationMessage: smartRuleLane.hydrationMessage,
      isRunningSmartGrouping: publicSmartGroupingRun.isBusy,
      smartGroupingRunMessage: publicSmartGroupingRun.message,
      smartGroupingRunTone: publicSmartGroupingRun.tone,
      isRunningSmartSeating: publicSmartSeatingRun.isBusy,
      smartSeatingRunMessage: publicSmartSeatingRun.message,
      smartSeatingRunTone: publicSmartSeatingRun.tone,
      plannerStatusLabel: plannerStatus.plannerStatusLabel,
      plannerStatusMessage: plannerStatus.plannerStatusMessage,
      plannerStatusTone: plannerStatus.plannerStatusTone,
      plannerConflictMessage: plannerStatus.plannerConflictMessage,
      isWorkspaceBusy, canEditSeatingSmartRules, hasPendingAutosave, hasWorkspace,
      students, seats, fixtures,
      studentsById, seatsById, fixturesById, groupsById,
      groupAssignmentsByStudentId,
      seatAssignmentsByStudentId,
      seatingPreferences, relationshipRules, fixedSeatRules, smartRulesRevision, smartRulesHydrated,
      groupAssignments, seatAssignments,
      ungroupedStudents, unseatedStudents, studentsByGroupId, studentBySeatId, zones,
      canUndo, canRedo,
    },
    smartRuleState: {
      activeSeatingSmartTool: smartRuleUiState.activeSeatingSmartTool,
      pendingRelationshipStudentIds: smartRuleUiState.pendingRelationshipStudentIds,
      pendingFixedSeatStudentId: smartRuleUiState.pendingFixedSeatStudentId,
      pendingFixedSeatSeatId: smartRuleUiState.pendingFixedSeatSeatId,
      editingFixedSeatRuleId: smartRuleUiState.editingFixedSeatRuleId,
      editingRelationshipRuleId: smartRuleUiState.editingRelationshipRuleId,
      editingNearTeacherRule: smartRuleUiState.editingNearTeacherRule,
      smartRuleFeedbackMessage: smartRuleUiState.feedbackMessage,
      canCommitPendingRelationshipRule: smartRuleUiState.canCommitPendingRelationshipRule,
      canCommitPendingFixedSeatRule: smartRuleUiState.canCommitPendingFixedSeatRule,
      setDraftSmartEnabled: smartRuleActions.setDraftSmartEnabled,
      setDraftUseHistoryEnabled: smartRuleActions.setDraftUseHistoryEnabled,
      setActiveSeatingSmartTool: smartRuleUiState.setActiveSeatingSmartTool,
      clearPendingRelationshipSelection: smartRuleUiState.clearPendingRelationshipSelection,
      setStudentNearTeacherEnabled: smartRuleActions.setStudentNearTeacherEnabled,
      replaceNearTeacherPreference: smartRuleActions.replaceNearTeacherPreference,
      handleSeatingSmartToolStudentSelection:
        smartRuleActions.handleSeatingSmartToolStudentSelection,
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
    },
    workspaceActions: {
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
      reloadActiveWorkspace,
      getResumableDraft: persistence.getResumableDraft,
      getClassWorkspaceSummary: persistence.getClassWorkspaceSummary,
      abandonDraft,
      persistCurrentWorkspaceToOverview: workspaceActions.persistCurrentWorkspaceToOverview,
      persistOverviewUiState: workspaceActions.persistOverviewUiState,
    },
    historyActions: {
      activateGroupingHistoryDraft: noopHistoryAction,
      deleteGroupingHistoryDraft: noopHistoryAction,
      activateSeatingHistoryDraft: noopHistoryAction,
      deleteSeatingHistoryDraft: noopHistoryAction,
      undoGroupingDraft,
      redoGroupingDraft,
      undoSeatingDraft,
      redoSeatingDraft,
    },
    mutationActions: {
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
    },
  });
}
