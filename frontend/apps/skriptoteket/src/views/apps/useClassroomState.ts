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

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { apiDelete, apiGet, apiPatch, apiPost, isApiError } from "../../api/client";
import type {
  DraftLanePatchPayload,
  DraftPersistenceLaneResult,
} from "./useDraftPersistenceLane";
import { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import {
  discardPlannerSession,
  preparePlannerAbandonDraft,
  preparePlannerExit,
  preparePlannerExport,
  preparePlannerHistoryAction,
  preparePlannerWorkspaceSwitch,
  type PlannerAbandonResult,
  type PlannerExitResult,
  type PlannerTransitionResult,
} from "./plannerTransitionPolicies";
import { usePlannerSessionController } from "./usePlannerSessionController";
import type {
  RosterSmartRuleLaneResult,
  RosterSmartRulePatchPayload,
} from "./useRosterSmartRuleLane";
import { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";
import { useSmartRuleUiState } from "./useSmartRuleUiState";
import {
  buildFixtureMap,
  buildGroupMap,
  buildSeatMap,
  buildStudentMap,
  createPlannerMutationActions,
  normalizeAssignments,
  reindexGroups,
} from "./classroomPlannerStoreMutations";
import type {
  ClassWorkspaceSummary,
  DraftHistoryStatus,
  DraftGroup,
  DraftWorkspaceResponse,
  GroupAssignment,
  PlanDraft,
  PlanDraftKind,
  RelationshipRule,
  RosterSmartRulesResponse,
  ResumablePlanDraft,
  RoomTemplate,
  Roster,
  SeatAssignment,
  Student,
  StudentPlanningMeta,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";

const EXIT_AUTOSAVE_TIMEOUT_MS = 1500;
const SMART_RULE_HYDRATION_FALLBACK_MESSAGE = "Kunde inte ladda smarta regler.";

type PlannerStatusTone = "neutral" | "success" | "warning" | "danger";

export const useClassroomState = defineStore("classroom-state", () => {
  const draft = ref<PlanDraft | null>(null);
  const roster = ref<Roster | null>(null);
  const template = ref<RoomTemplate | null>(null);
  const groups = ref<DraftGroup[]>([]);
  const groupAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const seatAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const studentPlanningMetaByStudentId = ref<Record<string, StudentPlanningMeta>>({});
  const seatingPreferences = ref<StudentSeatingPreference[]>([]);
  const relationshipRules = ref<RelationshipRule[]>([]);
  const smartRulesRevision = ref(0);
  const historyStatus = ref<DraftHistoryStatus>({
    can_undo: false,
    can_redo: false,
  });
  const historyActionInFlight = ref(false);

  const sessionController = usePlannerSessionController();
  const smartRuleUiState = useSmartRuleUiState({
    canEditSmartRules: () => canEditSeatingSmartRules.value,
  });

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

  const draftLane = useDraftPersistenceLane({
    canSchedule: () => !isWorkspaceBusy.value,
    getSessionToken: () => sessionController.sessionToken.value,
    normalizeErrorMessage: normalizeMutationError,
    persistDraft: async (draftId, patch) => {
      return await apiPatch<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draftId}`,
        patch,
      );
    },
    serializePatch: serializeDraftPatch,
    applyCommittedWorkspace: (workspace) => applyWorkspace(workspace),
    applyAcknowledgement: applyDraftSaveAcknowledgement,
  });

  const smartRuleLane = useRosterSmartRuleLane({
    canSchedule: () => !isWorkspaceBusy.value,
    getSessionToken: () => sessionController.sessionToken.value,
    normalizeErrorMessage: normalizeMutationError,
    persistSmartRules: async (rosterId, patch) => {
      return await apiPatch<RosterSmartRulesResponse>(
        `/api/v1/apps/classroom.group-seating-studio/rosters/${rosterId}/smart-rules`,
        patch,
      );
    },
    serializePatch: serializeSmartRulesPatch,
    applyCommittedRules: (rules) => applyRosterSmartRules(rules),
    applyAcknowledgement: applySmartRuleSaveAcknowledgement,
  });

  const hasWorkspace = computed(() => {
    return draft.value !== null && roster.value !== null;
  });

  const isWorkspaceBusy = computed(() => {
    return historyActionInFlight.value || sessionController.transitionDepth.value > 0;
  });

  const hasPendingAutosave = computed(() => {
    return draftLane.hasPendingChanges.value || smartRuleLane.hasPendingChanges.value;
  });

  const smartRulesHydrated = computed(() => smartRuleLane.isHydrated.value);

  const canEditSeatingSmartRules = computed(() => {
    return roster.value !== null && smartRuleLane.isHydrated.value && !isWorkspaceBusy.value;
  });

  const students = computed(() => roster.value?.students ?? []);
  const seats = computed(() => template.value?.seats ?? []);
  const fixtures = computed(() => template.value?.fixtures ?? []);

  const studentsById = computed(() => buildStudentMap(students.value));
  const seatsById = computed(() => buildSeatMap(seats.value));
  const fixturesById = computed(() => buildFixtureMap(fixtures.value));
  const groupsById = computed(() => buildGroupMap(groups.value));

  const studentPlanningMeta = computed(() => {
    return students.value
      .map((student) => studentPlanningMetaByStudentId.value[student.id] ?? null)
      .filter((meta): meta is StudentPlanningMeta => meta !== null);
  });

  const groupAssignments = computed<GroupAssignment[]>(() => {
    return Object.entries(groupAssignmentsByStudentId.value)
      .filter((entry) => typeof entry[1] === "string" && entry[1].length > 0)
      .map(([studentId, groupId]) => ({ student_id: studentId, group_id: groupId as string }));
  });

  const seatAssignments = computed<SeatAssignment[]>(() => {
    return Object.entries(seatAssignmentsByStudentId.value)
      .filter((entry) => typeof entry[1] === "string" && entry[1].length > 0)
      .map(([studentId, seatId]) => ({ student_id: studentId, seat_id: seatId as string }));
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

  const plannerConflictMessage = computed(() => {
    if (draftLane.status.value === "conflict") {
      return draftLane.message.value;
    }
    if (smartRuleLane.status.value === "conflict") {
      return smartRuleLane.message.value;
    }
    return null;
  });

  const plannerStatusLabel = computed(() => {
    if (plannerConflictMessage.value) {
      return "Konflikt";
    }
    if (draftLane.status.value === "error" || smartRuleLane.status.value === "error") {
      return "Inte sparad";
    }
    if (smartRuleLane.hydrationStatus.value === "error") {
      return "Smarta regler otillgängliga";
    }
    if (draftLane.isSaving.value || smartRuleLane.isSaving.value || hasPendingAutosave.value) {
      return "Sparar";
    }
    if (isWorkspaceBusy.value) {
      return "Arbetar";
    }
    if (draftLane.status.value === "saved" || smartRuleLane.status.value === "saved") {
      return "Sparad";
    }
    return "Ingen ändring";
  });

  const plannerStatusTone = computed<PlannerStatusTone>(() => {
    if (plannerConflictMessage.value || draftLane.status.value === "error" || smartRuleLane.status.value === "error") {
      return "danger";
    }
    if (smartRuleLane.hydrationStatus.value === "error") {
      return "warning";
    }
    if (draftLane.isSaving.value || smartRuleLane.isSaving.value || hasPendingAutosave.value || isWorkspaceBusy.value) {
      return "warning";
    }
    if (draftLane.status.value === "saved" || smartRuleLane.status.value === "saved") {
      return "success";
    }
    return "neutral";
  });

  const plannerStatusMessage = computed(() => {
    if (plannerConflictMessage.value) {
      return plannerConflictMessage.value;
    }
    if (draftLane.status.value === "error") {
      return draftLane.message.value;
    }
    if (smartRuleLane.status.value === "error") {
      return smartRuleLane.message.value;
    }
    if (smartRuleLane.hydrationStatus.value === "error") {
      return smartRuleLane.hydrationMessage.value;
    }
    return null;
  });

  function clearRosterSmartRules(options: { resetUiState?: boolean } = {}): void {
    seatingPreferences.value = [];
    relationshipRules.value = [];
    smartRulesRevision.value = 0;
    if (options.resetUiState ?? true) {
      smartRuleUiState.reset();
      return;
    }
    smartRuleUiState.clearPendingRelationshipSelection();
  }

  function applyWorkspace(workspace: DraftWorkspaceResponse): void {
    draft.value = workspace.draft;
    roster.value = workspace.roster;
    template.value = workspace.template ?? null;
    groups.value = reindexGroups([...workspace.groups].sort((left, right) => left.sort_order - right.sort_order));
    groupAssignmentsByStudentId.value = normalizeAssignments(workspace.group_assignments, "group_id");
    seatAssignmentsByStudentId.value = normalizeAssignments(workspace.seat_assignments, "seat_id");
    studentPlanningMetaByStudentId.value = Object.fromEntries(
      workspace.student_planning_meta.map((meta) => [meta.student_id, meta]),
    );
    historyStatus.value = workspace.history_status;
    historyActionInFlight.value = false;
  }

  function applyRosterSmartRules(rules: RosterSmartRulesResponse): void {
    seatingPreferences.value = normalizeSeatingPreferencesCollection(rules.seating_preferences);
    relationshipRules.value = rules.relationship_rules.map((rule) => ({
      ...rule,
      student_ids: [...rule.student_ids],
    }));
    smartRulesRevision.value = rules.revision;
    smartRuleLane.applyHydratedRules();
  }

  function applyDraftSaveAcknowledgement(workspace: DraftWorkspaceResponse): void {
    if (!draft.value || draft.value.id !== workspace.draft.id) {
      return;
    }
    draft.value = {
      ...draft.value,
      revision: workspace.draft.revision,
      last_opened_at: workspace.draft.last_opened_at,
    };
    historyStatus.value = workspace.history_status;
    historyActionInFlight.value = false;
  }

  function applySmartRuleSaveAcknowledgement(rules: RosterSmartRulesResponse): void {
    if (!roster.value || roster.value.id !== rules.roster_id) {
      return;
    }
    smartRulesRevision.value = rules.revision;
    smartRuleLane.applyHydratedRules();
  }

  function serializeDraftPatch(): DraftLanePatchPayload {
    return {
      expected_revision: draft.value?.revision ?? null,
      smart_enabled: draft.value?.smart_enabled ?? false,
      groups: groups.value.map((group) => ({ ...group })),
      group_assignments: groupAssignments.value.map((assignment) => ({ ...assignment })),
      seat_assignments: seatAssignments.value.map((assignment) => ({ ...assignment })),
      student_planning_meta: studentPlanningMeta.value.map((meta) => ({ ...meta })),
    };
  }

  function serializeSmartRulesPatch(): RosterSmartRulePatchPayload {
    return {
      expected_revision: smartRulesRevision.value,
      seating_preferences: normalizeSeatingPreferencesCollection(seatingPreferences.value),
      relationship_rules: relationshipRules.value.map((rule) => ({
        ...rule,
        student_ids: [...rule.student_ids],
      })),
    };
  }

  function createTransitionController() {
    return {
      draft: draft.value,
      flushDraftPersistenceLane: async (): Promise<DraftPersistenceLaneResult> => {
        return await draftLane.flushPendingChanges();
      },
      flushSmartRuleLane: async (): Promise<RosterSmartRuleLaneResult> => {
        return await smartRuleLane.flushPendingChanges();
      },
      discardDraftPersistenceLane: (): void => {
        draftLane.discardPendingChanges();
      },
      discardSmartRuleLane: (): void => {
        smartRuleLane.discardPendingChanges();
      },
    };
  }

  function syncVisibleSessionBindings(): void {
    draftLane.syncBoundDraft(draft.value?.id ?? null);
    smartRuleLane.syncBoundRoster(roster.value?.id ?? null);
  }

  function discardPendingSessionWork(): void {
    sessionController.invalidateAsyncState();
    historyActionInFlight.value = false;
    discardPlannerSession(createTransitionController());
  }

  function setDraftSmartEnabled(enabled: boolean): void {
    if (!draft.value || isWorkspaceBusy.value) {
      return;
    }
    if ((draft.value.smart_enabled ?? false) === enabled) {
      return;
    }
    draft.value = {
      ...draft.value,
      smart_enabled: enabled,
    };
    syncVisibleSessionBindings();
    draftLane.markDirty();
  }

  function isStudentMarkedNearTeacher(studentId: string): boolean {
    return seatingPreferences.value.some(
      (preference) => preference.student_id === studentId && preference.near_teacher === true,
    );
  }

  function updateSeatingPreference(studentId: string, enabled: boolean): void {
    const existingIndex = seatingPreferences.value.findIndex(
      (preference) => preference.student_id === studentId,
    );
    if (enabled) {
      if (existingIndex >= 0) {
        return;
      }
      seatingPreferences.value = [
        ...seatingPreferences.value,
        {
          student_id: studentId,
          near_teacher: true,
        },
      ];
      syncVisibleSessionBindings();
      smartRuleLane.markDirty();
      smartRuleUiState.clearFeedback();
      return;
    }

    if (existingIndex < 0) {
      return;
    }
    seatingPreferences.value = seatingPreferences.value.filter(
      (preference) => preference.student_id !== studentId,
    );
    syncVisibleSessionBindings();
    smartRuleLane.markDirty();
    smartRuleUiState.clearFeedback();
  }

  function toggleNearTeacherPreference(studentId: string): void {
    updateSeatingPreference(studentId, !isStudentMarkedNearTeacher(studentId));
  }

  function createRelationshipRuleId(): string {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return `relationship-rule-${Date.now()}`;
  }

  function commitPendingRelationshipRule(): boolean {
    const activeTool = smartRuleUiState.activeSeatingSmartTool.value;
    if (activeTool !== "keep_near" && activeTool !== "keep_apart") {
      return false;
    }
    if (!smartRuleUiState.canCommitPendingRelationshipRule.value || !canEditSeatingSmartRules.value) {
      return false;
    }

    const overlappingStudentIds = new Set(
      relationshipRules.value.flatMap((rule) =>
        rule.student_ids.filter((studentId) =>
          smartRuleUiState.pendingRelationshipStudentIds.value.includes(studentId),
        ),
      ),
    );
    if (overlappingStudentIds.size > 0) {
      smartRuleUiState.setFeedbackMessage("En elev kan bara ingå i en relationsregel åt gången.");
      return false;
    }

    relationshipRules.value = [
      ...relationshipRules.value,
      {
        id: createRelationshipRuleId(),
        kind: activeTool,
        student_ids: [...smartRuleUiState.pendingRelationshipStudentIds.value],
      },
    ];
    smartRuleUiState.clearPendingRelationshipSelection();
    syncVisibleSessionBindings();
    smartRuleLane.markDirty();
    return true;
  }

  function deleteRelationshipRule(ruleId: string): void {
    if (!canEditSeatingSmartRules.value) {
      return;
    }
    const nextRules = relationshipRules.value.filter((rule) => rule.id !== ruleId);
    if (nextRules.length === relationshipRules.value.length) {
      return;
    }
    relationshipRules.value = nextRules;
    smartRuleUiState.clearFeedback();
    syncVisibleSessionBindings();
    smartRuleLane.markDirty();
  }

  function handleSeatingSmartToolStudentSelection(studentId: string): boolean {
    if (
      !studentsById.value[studentId]
      || !smartRuleUiState.activeSeatingSmartTool.value
      || isWorkspaceBusy.value
    ) {
      return false;
    }

    if (smartRuleUiState.activeSeatingSmartTool.value === "near_teacher") {
      toggleNearTeacherPreference(studentId);
      return true;
    }

    smartRuleUiState.togglePendingRelationshipStudent(studentId);
    return true;
  }

  async function prepareForWorkspaceSwitch(messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }): Promise<PlannerTransitionResult> {
    syncVisibleSessionBindings();
    return await preparePlannerWorkspaceSwitch(createTransitionController(), messages);
  }

  async function prepareForExport(messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }): Promise<PlannerTransitionResult> {
    syncVisibleSessionBindings();
    return await preparePlannerExport(createTransitionController(), messages);
  }

  async function prepareForPlannerExit(): Promise<PlannerExitResult> {
    syncVisibleSessionBindings();
    return await preparePlannerExit(createTransitionController(), EXIT_AUTOSAVE_TIMEOUT_MS, {
      conflictMessage: "Lös sparkonflikten innan du avslutar Klassrumskartan.",
      fallbackMessage: "Kunde inte avsluta Klassrumskartan just nu.",
    });
  }

  async function retrySmartRuleHydration(): Promise<void> {
    const activeRosterId = roster.value?.id ?? null;
    if (!activeRosterId) {
      return;
    }
    const requestSessionToken = sessionController.sessionToken.value;
    smartRuleLane.markHydrating();
    try {
      const rules = await apiGet<RosterSmartRulesResponse>(
        `/api/v1/apps/classroom.group-seating-studio/rosters/${activeRosterId}/smart-rules`,
      );
      if (
        sessionController.sessionToken.value !== requestSessionToken
        || roster.value?.id !== activeRosterId
      ) {
        return;
      }
      applyRosterSmartRules(rules);
    } catch (error: unknown) {
      if (
        sessionController.sessionToken.value !== requestSessionToken
        || roster.value?.id !== activeRosterId
      ) {
        return;
      }
      smartRuleLane.failHydration(
        normalizeMutationError(error, SMART_RULE_HYDRATION_FALLBACK_MESSAGE),
      );
    }
  }

  function clearWorkspace(): void {
    sessionController.clearSession();
    draftLane.resetBoundDraft(null);
    smartRuleLane.bindRoster(null);
    smartRuleUiState.reset();
    draft.value = null;
    roster.value = null;
    template.value = null;
    groups.value = [];
    groupAssignmentsByStudentId.value = {};
    seatAssignmentsByStudentId.value = {};
    studentPlanningMetaByStudentId.value = {};
    seatingPreferences.value = [];
    relationshipRules.value = [];
    smartRulesRevision.value = 0;
    historyStatus.value = {
      can_undo: false,
      can_redo: false,
    };
    historyActionInFlight.value = false;
  }

  async function loadWorkspace(draftId: string): Promise<void> {
    const requestId = sessionController.createWorkspaceLoadRequest();
    sessionController.beginWorkspaceTransition();
    try {
      const workspace = await apiGet<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draftId}/workspace`,
      );
      if (!sessionController.isCurrentWorkspaceLoadRequest(requestId)) {
        return;
      }

      sessionController.replaceSession({
        draftId: workspace.draft.id,
        rosterId: workspace.roster.id,
      });
      draftLane.resetBoundDraft(workspace.draft.id);
      smartRuleLane.bindRoster(workspace.roster.id);
      clearRosterSmartRules({ resetUiState: true });
      applyWorkspace(workspace);

      try {
        const rules = await apiGet<RosterSmartRulesResponse>(
          `/api/v1/apps/classroom.group-seating-studio/rosters/${workspace.roster.id}/smart-rules`,
        );
        if (!sessionController.isCurrentWorkspaceLoadRequest(requestId)) {
          return;
        }
        applyRosterSmartRules(rules);
      } catch (error: unknown) {
        if (!sessionController.isCurrentWorkspaceLoadRequest(requestId)) {
          return;
        }
        smartRuleLane.failHydration(
          normalizeMutationError(error, SMART_RULE_HYDRATION_FALLBACK_MESSAGE),
        );
      }
    } finally {
      sessionController.endWorkspaceTransition();
    }
  }

  async function reloadActiveWorkspace(): Promise<void> {
    if (!draft.value) {
      return;
    }
    await loadWorkspace(draft.value.id);
  }

  async function runLifecycleLoad(
    url: string,
    payload?: Record<string, string | null>,
  ): Promise<void> {
    sessionController.beginWorkspaceTransition();
    try {
      const createdDraft = payload === undefined
        ? await apiPost<PlanDraft>(url)
        : await apiPost<PlanDraft>(url, payload);
      await loadWorkspace(createdDraft.id);
    } finally {
      sessionController.endWorkspaceTransition();
    }
  }

  async function resolveDraft(
    rosterId: string,
    templateId: string | null,
    draftKind: PlanDraftKind = "seating",
  ): Promise<void> {
    await runLifecycleLoad("/api/v1/apps/classroom.group-seating-studio/drafts/resolve", {
      roster_id: rosterId,
      draft_kind: draftKind,
      template_id: templateId,
    });
  }

  async function startNewGroupingDraft(
    rosterId: string,
    templateId: string | null,
  ): Promise<void> {
    await runLifecycleLoad("/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new", {
      roster_id: rosterId,
      template_id: templateId,
    });
  }

  async function startNewSeatingDraft(
    rosterId: string,
    templateId: string,
  ): Promise<void> {
    await runLifecycleLoad("/api/v1/apps/classroom.group-seating-studio/drafts/seating/new", {
      roster_id: rosterId,
      template_id: templateId,
    });
  }

  async function activateGroupingHistoryDraft(draftId: string): Promise<void> {
    await runLifecycleLoad(
      `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${draftId}/activate`,
    );
  }

  async function activateSeatingHistoryDraft(draftId: string): Promise<void> {
    await runLifecycleLoad(
      `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${draftId}/activate`,
    );
  }

  async function deleteGroupingHistoryDraft(draftId: string): Promise<void> {
    sessionController.beginWorkspaceTransition();
    try {
      await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${draftId}`);
    } finally {
      sessionController.endWorkspaceTransition();
    }
  }

  async function deleteSeatingHistoryDraft(draftId: string): Promise<void> {
    sessionController.beginWorkspaceTransition();
    try {
      await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/drafts/seating/${draftId}`);
    } finally {
      sessionController.endWorkspaceTransition();
    }
  }

  async function runHistoryAction(action: "undo" | "redo"): Promise<void> {
    if (!draft.value || historyActionInFlight.value) {
      return;
    }

    syncVisibleSessionBindings();
    const historyPreparation = await preparePlannerHistoryAction(createTransitionController());
    if (historyPreparation.status === "blocked" || !draft.value) {
      return;
    }

    historyActionInFlight.value = true;
    try {
      const workspace = await apiPost<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}/${action}`,
      );
      applyWorkspace(workspace);
    } finally {
      historyActionInFlight.value = false;
    }
  }

  async function undoGroupingDraft(): Promise<void> {
    await runHistoryAction("undo");
  }

  async function redoGroupingDraft(): Promise<void> {
    await runHistoryAction("redo");
  }

  async function undoSeatingDraft(): Promise<void> {
    await runHistoryAction("undo");
  }

  async function redoSeatingDraft(): Promise<void> {
    await runHistoryAction("redo");
  }

  async function getResumableDraft(): Promise<ResumablePlanDraft | null> {
    return await apiGet<ResumablePlanDraft | null>(
      "/api/v1/apps/classroom.group-seating-studio/drafts/resumable",
    );
  }

  async function getClassWorkspaceSummary(rosterId: string): Promise<ClassWorkspaceSummary> {
    return await apiGet<ClassWorkspaceSummary>(
      `/api/v1/apps/classroom.group-seating-studio/rosters/${rosterId}/workspace-summary`,
    );
  }

  async function abandonDraft(
    draftId?: string,
    options: { continueWithoutSavingSmartRules?: boolean } = {},
  ): Promise<PlannerAbandonResult> {
    const targetDraftId = draftId ?? draft.value?.id ?? null;
    if (!targetDraftId) {
      clearWorkspace();
      return { status: "saved" };
    }

    syncVisibleSessionBindings();
    const abandonPreparation = await preparePlannerAbandonDraft(createTransitionController(), {
      continueAnywayMessage:
        "Fortsätter du nu förlorar du osparade klassövergripande smarta regler för klassen.",
    });
    if (
      abandonPreparation.status === "confirm-discard"
      && !options.continueWithoutSavingSmartRules
    ) {
      return abandonPreparation;
    }

    if (abandonPreparation.status === "confirm-discard") {
      discardPendingSessionWork();
    }

    draftLane.discardPendingChanges();
    await apiPost<PlanDraft>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${targetDraftId}/abandon`,
    );
    if (draft.value?.id === targetDraftId) {
      clearWorkspace();
    }
    return { status: "saved" };
  }

  const {
    randomizeGroups,
    randomizeSeating,
    assignStudentToGroup,
    removeStudentFromGroup,
    clearGroupingAssignments,
    assignStudentToSeat,
    swapSeatAssignments,
    clearSeatAssignment,
    clearSeatingAssignments,
    addGroup,
    renameGroup,
    moveGroup,
    removeGroup,
    setStudentPlanningMeta,
    resetStudentPlanningMeta,
  } = createPlannerMutationActions({
    students,
    studentsById,
    seatsById,
    groupsById,
    groups,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    studentPlanningMetaByStudentId,
    canMutate: () => !isWorkspaceBusy.value,
    markDirty: () => {
      syncVisibleSessionBindings();
      draftLane.markDirty();
    },
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
    plannerStatusLabel,
    plannerStatusMessage,
    plannerStatusTone,
    plannerConflictMessage,
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
    studentPlanningMetaByStudentId,
    seatingPreferences,
    relationshipRules,
    smartRulesRevision,
    smartRulesHydrated,
    activeSeatingSmartTool: smartRuleUiState.activeSeatingSmartTool,
    pendingRelationshipStudentIds: smartRuleUiState.pendingRelationshipStudentIds,
    smartRuleFeedbackMessage: smartRuleUiState.feedbackMessage,
    studentPlanningMeta,
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
    clearWorkspace,
    discardPendingSessionWork,
    prepareForWorkspaceSwitch,
    prepareForExport,
    prepareForPlannerExit,
    retrySmartRuleHydration,
    resolveDraft,
    startNewGroupingDraft,
    startNewSeatingDraft,
    loadWorkspace,
    reloadActiveWorkspace,
    activateGroupingHistoryDraft,
    deleteGroupingHistoryDraft,
    activateSeatingHistoryDraft,
    deleteSeatingHistoryDraft,
    undoGroupingDraft,
    redoGroupingDraft,
    undoSeatingDraft,
    redoSeatingDraft,
    getResumableDraft,
    getClassWorkspaceSummary,
    abandonDraft,
    setDraftSmartEnabled,
    setActiveSeatingSmartTool: smartRuleUiState.setActiveSeatingSmartTool,
    clearPendingRelationshipSelection: smartRuleUiState.clearPendingRelationshipSelection,
    handleSeatingSmartToolStudentSelection,
    commitPendingRelationshipRule,
    deleteRelationshipRule,
    isStudentMarkedNearTeacher,
    isStudentInPendingRelationshipSelection: smartRuleUiState.isStudentInPendingRelationshipSelection,
    assignStudentToGroup,
    removeStudentFromGroup,
    clearGroupingAssignments,
    assignStudentToSeat,
    swapSeatAssignments,
    clearSeatAssignment,
    clearSeatingAssignments,
    addGroup,
    renameGroup,
    moveGroup,
    removeGroup,
    randomizeGroups,
    randomizeSeating,
    setStudentPlanningMeta,
    resetStudentPlanningMeta,
  };
});
