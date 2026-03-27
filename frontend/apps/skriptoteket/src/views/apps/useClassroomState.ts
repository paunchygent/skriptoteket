/**
 * Classroom planner Pinia store.
 *
 * This store owns the mutable Klassrumskartan draft workspace used by the
 * planner SPA. It hydrates the backend workspace contract, exposes normalized
 * lookup maps for the drag-and-drop UI, schedules optimistic autosave patches,
 * and coordinates the shipped grouping, seating, and student-note workflow
 * without carrying superseded solver-era planner state.
 */

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { ApiError, apiDelete, apiGet, apiPatch, apiPost, isApiError } from "../../api/client";
import {
  type ClassWorkspaceSummary,
  type DraftHistoryStatus,
  type DraftGroup,
  type DraftWorkspaceResponse,
  type GroupAssignment,
  type PlanDraft,
  type PlanDraftKind,
  type RelationshipRule,
  type RosterSmartRulesResponse,
  type SeatingSmartTool,
  type ResumablePlanDraft,
  type RoomTemplate,
  type Roster,
  type SaveStatus,
  type SeatAssignment,
  type Student,
  type StudentPlanningMeta,
  type StudentSeatingPreference,
} from "./classroomPlannerTypes";
import {
  buildFixtureMap,
  buildGroupMap,
  buildSeatMap,
  buildStudentMap,
  createPlannerMutationActions,
  normalizeAssignments,
  reindexGroups,
} from "./classroomPlannerStoreMutations";

const AUTOSAVE_DELAY_MS = 900;
type PersistLaneResult = "ok" | "conflict" | "error" | "cancelled";

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
  const smartRulesHydrated = ref(false);
  const activeSeatingSmartTool = ref<SeatingSmartTool | null>(null);
  const pendingRelationshipStudentIds = ref<string[]>([]);
  const smartRuleFeedbackMessage = ref<string | null>(null);
  const historyStatus = ref<DraftHistoryStatus>({
    can_undo: false,
    can_redo: false,
  });
  const hasPendingDraftAutosave = ref(false);
  const hasPendingSmartRuleAutosave = ref(false);
  const historyActionInFlight = ref(false);
  const workspaceTransitionDepth = ref(0);
  const saveStatus = ref<SaveStatus>("idle");
  const saveMessage = ref<string | null>(null);

  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
  let saveInFlight = false;
  let saveQueued = false;
  let asyncStateGeneration = 0;
  let workspaceLoadRequestId = 0;

  const isWorkspaceBusy = computed(() => {
    return historyActionInFlight.value || workspaceTransitionDepth.value > 0;
  });

  const hasWorkspace = computed(() => {
    return draft.value !== null && roster.value !== null;
  });

  const hasPendingAutosave = computed(() => {
    return hasPendingDraftAutosave.value || hasPendingSmartRuleAutosave.value;
  });

  const canEditSeatingSmartRules = computed(() => {
    return roster.value !== null && smartRulesHydrated.value && !isWorkspaceBusy.value;
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
      && (historyStatus.value.can_undo || hasPendingAutosave.value)
    );
  });

  const canRedo = computed(() => {
    return draft.value !== null && !isWorkspaceBusy.value && historyStatus.value.can_redo;
  });

  const canCommitPendingRelationshipRule = computed(() => {
    return (
      (activeSeatingSmartTool.value === "keep_near" || activeSeatingSmartTool.value === "keep_apart")
      && pendingRelationshipStudentIds.value.length >= 2
      && !isWorkspaceBusy.value
    );
  });

  function clearSmartRuleFeedback(): void {
    smartRuleFeedbackMessage.value = null;
  }

  function clearRosterSmartRules(options: { resetUiState?: boolean } = {}): void {
    seatingPreferences.value = [];
    relationshipRules.value = [];
    smartRulesRevision.value = 0;
    smartRulesHydrated.value = false;
    clearSmartRuleFeedback();
    if (options.resetUiState ?? true) {
      resetSeatingSmartRuleUiState();
      return;
    }
    clearPendingRelationshipSelection();
  }

  function clearPendingRelationshipSelection(): void {
    pendingRelationshipStudentIds.value = [];
    clearSmartRuleFeedback();
  }

  function resetSeatingSmartRuleUiState(): void {
    activeSeatingSmartTool.value = null;
    clearPendingRelationshipSelection();
  }

  function isStudentMarkedNearTeacher(studentId: string): boolean {
    return seatingPreferences.value.some((preference) => preference.student_id === studentId);
  }

  function isStudentInPendingRelationshipSelection(studentId: string): boolean {
    return pendingRelationshipStudentIds.value.includes(studentId);
  }

  function setActiveSeatingSmartTool(tool: SeatingSmartTool | null): void {
    if (tool !== null && !canEditSeatingSmartRules.value) {
      return;
    }
    if (activeSeatingSmartTool.value === tool) {
      activeSeatingSmartTool.value = null;
      clearPendingRelationshipSelection();
      return;
    }
    activeSeatingSmartTool.value = tool;
    clearPendingRelationshipSelection();
  }

  function canMutateSeatingSmartRules(): boolean {
    return canEditSeatingSmartRules.value;
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
      markSmartRulesDirty();
      clearSmartRuleFeedback();
      return;
    }

    if (existingIndex < 0) {
      return;
    }
    seatingPreferences.value = seatingPreferences.value.filter(
      (preference) => preference.student_id !== studentId,
    );
    markSmartRulesDirty();
    clearSmartRuleFeedback();
  }

  function toggleNearTeacherPreference(studentId: string): void {
    updateSeatingPreference(studentId, !isStudentMarkedNearTeacher(studentId));
  }

  function togglePendingRelationshipStudent(studentId: string): void {
    if (isStudentInPendingRelationshipSelection(studentId)) {
      pendingRelationshipStudentIds.value = pendingRelationshipStudentIds.value.filter(
        (pendingStudentId) => pendingStudentId !== studentId,
      );
    } else {
      pendingRelationshipStudentIds.value = [...pendingRelationshipStudentIds.value, studentId];
    }
    clearSmartRuleFeedback();
  }

  function createRelationshipRuleId(): string {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return `relationship-rule-${Date.now()}`;
  }

  function commitPendingRelationshipRule(): boolean {
    const activeTool = activeSeatingSmartTool.value;
    if (
      activeTool !== "keep_near"
      && activeTool !== "keep_apart"
    ) {
      return false;
    }
    if (!canCommitPendingRelationshipRule.value || !canMutateSeatingSmartRules()) {
      return false;
    }

    const overlappingStudentIds = new Set(
      relationshipRules.value.flatMap((rule) =>
        rule.student_ids.filter((studentId) => pendingRelationshipStudentIds.value.includes(studentId)),
      ),
    );
    if (overlappingStudentIds.size > 0) {
      smartRuleFeedbackMessage.value = "En elev kan bara ingå i en relationsregel åt gången.";
      return false;
    }

    relationshipRules.value = [
      ...relationshipRules.value,
      {
        id: createRelationshipRuleId(),
        kind: activeTool,
        student_ids: [...pendingRelationshipStudentIds.value],
      },
    ];
    clearPendingRelationshipSelection();
    markSmartRulesDirty();
    return true;
  }

  function deleteRelationshipRule(ruleId: string): void {
    if (!canMutateSeatingSmartRules()) {
      return;
    }
    const nextRules = relationshipRules.value.filter((rule) => rule.id !== ruleId);
    if (nextRules.length === relationshipRules.value.length) {
      return;
    }
    relationshipRules.value = nextRules;
    clearSmartRuleFeedback();
    markSmartRulesDirty();
  }

  function handleSeatingSmartToolStudentSelection(studentId: string): boolean {
    if (
      !studentsById.value[studentId]
      || !activeSeatingSmartTool.value
      || isWorkspaceBusy.value
    ) {
      return false;
    }

    if (activeSeatingSmartTool.value === "near_teacher") {
      toggleNearTeacherPreference(studentId);
      return true;
    }

    togglePendingRelationshipStudent(studentId);
    return true;
  }

  function beginWorkspaceTransition(): void {
    workspaceTransitionDepth.value += 1;
  }

  function endWorkspaceTransition(): void {
    workspaceTransitionDepth.value = Math.max(0, workspaceTransitionDepth.value - 1);
  }

  function clearAutosaveTimer(): void {
    if (autosaveTimer) {
      clearTimeout(autosaveTimer);
      autosaveTimer = null;
    }
  }

  function invalidateAsyncState(): void {
    asyncStateGeneration += 1;
    workspaceLoadRequestId += 1;
  }

  function markDirty(): void {
    if (isWorkspaceBusy.value) {
      return;
    }
    hasPendingDraftAutosave.value = true;
    scheduleAutosave();
  }

  function markSmartRulesDirty(): void {
    if (isWorkspaceBusy.value) {
      return;
    }
    hasPendingSmartRuleAutosave.value = true;
    scheduleAutosave();
  }

  function applyWorkspace(
    workspace: DraftWorkspaceResponse,
    options: { preserveActiveSeatingSmartTool?: boolean } = {},
  ): void {
    clearAutosaveTimer();
    saveQueued = false;
    if (options.preserveActiveSeatingSmartTool) {
      clearPendingRelationshipSelection();
    } else {
      resetSeatingSmartRuleUiState();
    }
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
    hasPendingDraftAutosave.value = false;
  }

  function applyRosterSmartRules(
    rules: RosterSmartRulesResponse,
    options: { preserveActiveSeatingSmartTool?: boolean } = {},
  ): void {
    if (!options.preserveActiveSeatingSmartTool) {
      resetSeatingSmartRuleUiState();
    } else {
      clearPendingRelationshipSelection();
    }
    seatingPreferences.value = [...rules.seating_preferences];
    relationshipRules.value = [...rules.relationship_rules];
    smartRulesRevision.value = rules.revision;
    smartRulesHydrated.value = true;
    hasPendingSmartRuleAutosave.value = false;
  }

  function serializeDraftPatch(): Record<string, unknown> {
    return {
      expected_revision: draft.value?.revision ?? null,
      smart_enabled: draft.value?.smart_enabled ?? false,
      groups: groups.value,
      group_assignments: groupAssignments.value,
      seat_assignments: seatAssignments.value,
      student_planning_meta: studentPlanningMeta.value,
    };
  }

  function serializeSmartRulesPatch(): Record<string, unknown> {
    return {
      expected_revision: smartRulesRevision.value,
      seating_preferences: seatingPreferences.value,
      relationship_rules: relationshipRules.value,
    };
  }

  function applySaveSuccessState(): void {
    saveStatus.value = "saved";
    saveMessage.value = null;
  }

  function applySaveFailureState(error: unknown, fallbackMessage: string): "conflict" | "error" {
    if (error instanceof ApiError && error.status === 409) {
      saveStatus.value = "conflict";
      saveMessage.value = error.message || fallbackMessage;
      return "conflict";
    }
    if (saveStatus.value !== "conflict") {
      saveStatus.value = "error";
      saveMessage.value = normalizeMutationError(error, fallbackMessage);
    }
    return "error";
  }

  async function persistSmartRulesLane(saveGeneration: number): Promise<PersistLaneResult> {
    if (!roster.value || !hasPendingSmartRuleAutosave.value) {
      return "ok";
    }
    try {
      const rules = await apiPatch<RosterSmartRulesResponse>(
        `/api/v1/apps/classroom.group-seating-studio/rosters/${roster.value.id}/smart-rules`,
        serializeSmartRulesPatch(),
      );
      if (saveGeneration !== asyncStateGeneration) {
        return "cancelled";
      }
      applyRosterSmartRules(rules, { preserveActiveSeatingSmartTool: true });
      return "ok";
    } catch (error: unknown) {
      if (saveGeneration !== asyncStateGeneration) {
        return "cancelled";
      }
      return applySaveFailureState(
        error,
        "Smarta regler har ändrats i en annan flik. Ladda om arbetsytan innan du fortsätter.",
      );
    }
  }

  async function persistDraftLane(saveGeneration: number): Promise<PersistLaneResult> {
    if (!draft.value || !hasPendingDraftAutosave.value) {
      return "ok";
    }
    try {
      const workspace = await apiPatch<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}`,
        serializeDraftPatch(),
      );
      if (saveGeneration !== asyncStateGeneration) {
        return "cancelled";
      }
      applyWorkspace(workspace, { preserveActiveSeatingSmartTool: true });
      return "ok";
    } catch (error: unknown) {
      if (saveGeneration !== asyncStateGeneration) {
        return "cancelled";
      }
      return applySaveFailureState(
        error,
        "Utkastet har ändrats i en annan flik. Ladda om arbetsytan innan du fortsätter.",
      );
    }
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

  async function persistPendingChanges(): Promise<void> {
    if (!draft.value || !roster.value) {
      return;
    }
    if (saveInFlight) {
      saveQueued = true;
      return;
    }

    saveInFlight = true;
    const saveGeneration = asyncStateGeneration;
    try {
      const smartRuleResult = await persistSmartRulesLane(saveGeneration);
      if (smartRuleResult === "cancelled") {
        return;
      }
      const draftResult = await persistDraftLane(saveGeneration);
      if (draftResult === "cancelled") {
        return;
      }
      if (smartRuleResult === "ok" && draftResult === "ok") {
        applySaveSuccessState();
      }
    } finally {
      saveInFlight = false;
      if (saveQueued && saveStatus.value !== "conflict") {
        saveQueued = false;
        await persistPendingChanges();
      }
    }
  }

  function scheduleAutosave(): void {
    if (!draft.value) {
      return;
    }
    clearAutosaveTimer();
    saveQueued = false;
    saveStatus.value = "saving";
    autosaveTimer = setTimeout(() => {
      void persistPendingChanges();
    }, AUTOSAVE_DELAY_MS);
  }

  function clearWorkspace(): void {
    cancelPendingSave();
    clearRosterSmartRules();
    draft.value = null;
    roster.value = null;
    template.value = null;
    groups.value = [];
    groupAssignmentsByStudentId.value = {};
    seatAssignmentsByStudentId.value = {};
    studentPlanningMetaByStudentId.value = {};
    historyStatus.value = {
      can_undo: false,
      can_redo: false,
    };
    historyActionInFlight.value = false;
    workspaceTransitionDepth.value = 0;
    hasPendingDraftAutosave.value = false;
    hasPendingSmartRuleAutosave.value = false;
    saveStatus.value = "idle";
    saveMessage.value = null;
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
    markDirty();
  }

  async function waitForPendingSave(): Promise<void> {
    while (saveInFlight) {
      await new Promise((resolve) => window.setTimeout(resolve, 10));
    }
  }

  function cancelPendingSave(): void {
    clearAutosaveTimer();
    saveQueued = false;
    invalidateAsyncState();
    historyActionInFlight.value = false;
    hasPendingDraftAutosave.value = false;
    hasPendingSmartRuleAutosave.value = false;
  }

  async function flushPendingSave(): Promise<boolean> {
    if (!draft.value) {
      return true;
    }

    const hadScheduledSave = autosaveTimer !== null;
    const hasDirtyLanes = hasPendingDraftAutosave.value || hasPendingSmartRuleAutosave.value;
    clearAutosaveTimer();
    if (saveInFlight) {
      await waitForPendingSave();
      return saveStatus.value !== "conflict" && saveStatus.value !== "error";
    }
    if (hadScheduledSave || saveQueued || hasDirtyLanes) {
      saveQueued = false;
      saveStatus.value = "saving";
      await persistPendingChanges();
    }

    return saveStatus.value !== "conflict" && saveStatus.value !== "error";
  }

  async function runHistoryAction(action: "undo" | "redo"): Promise<void> {
    if (!draft.value || historyActionInFlight.value) {
      return;
    }

    const flushSucceeded = await flushPendingSave();
    if (!flushSucceeded || !draft.value) {
      return;
    }

    historyActionInFlight.value = true;
    saveStatus.value = "saving";
    saveMessage.value = null;
    try {
      const workspace = await apiPost<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}/${action}`,
      );
      applyWorkspace(workspace);
      applySaveSuccessState();
    } catch (error: unknown) {
      historyActionInFlight.value = false;
      saveStatus.value = "error";
      saveMessage.value = normalizeMutationError(
        error,
        action === "undo" ? "Kunde inte ångra ändringen." : "Kunde inte göra om ändringen.",
      );
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

  async function resolveDraft(
    rosterId: string,
    templateId: string | null,
    draftKind: PlanDraftKind = "seating",
  ): Promise<void> {
    beginWorkspaceTransition();
    try {
      saveStatus.value = "saving";
      saveMessage.value = null;
      const resolvedDraft = await apiPost<PlanDraft>(
        "/api/v1/apps/classroom.group-seating-studio/drafts/resolve",
        {
          roster_id: rosterId,
          draft_kind: draftKind,
          template_id: templateId,
        },
      );
      await loadWorkspace(resolvedDraft.id);
    } finally {
      endWorkspaceTransition();
    }
  }

  async function startNewGroupingDraft(
    rosterId: string,
    templateId: string | null,
  ): Promise<void> {
    beginWorkspaceTransition();
    try {
      saveStatus.value = "saving";
      saveMessage.value = null;
      const createdDraft = await apiPost<PlanDraft>(
        "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new",
        {
          roster_id: rosterId,
          template_id: templateId,
        },
      );
      await loadWorkspace(createdDraft.id);
    } finally {
      endWorkspaceTransition();
    }
  }

  async function startNewSeatingDraft(
    rosterId: string,
    templateId: string,
  ): Promise<void> {
    beginWorkspaceTransition();
    try {
      saveStatus.value = "saving";
      saveMessage.value = null;
      const createdDraft = await apiPost<PlanDraft>(
        "/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
        {
          roster_id: rosterId,
          template_id: templateId,
        },
      );
      await loadWorkspace(createdDraft.id);
    } finally {
      endWorkspaceTransition();
    }
  }

  async function loadWorkspace(draftId: string): Promise<void> {
    const requestId = ++workspaceLoadRequestId;
    beginWorkspaceTransition();
    try {
      const workspace = await apiGet<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draftId}/workspace`,
      );
      if (requestId !== workspaceLoadRequestId) {
        return;
      }
      clearRosterSmartRules();
      applyWorkspace(workspace);
      try {
        const rules = await apiGet<RosterSmartRulesResponse>(
          `/api/v1/apps/classroom.group-seating-studio/rosters/${workspace.roster.id}/smart-rules`,
        );
        if (requestId !== workspaceLoadRequestId) {
          return;
        }
        applyRosterSmartRules(rules, { preserveActiveSeatingSmartTool: true });
        applySaveSuccessState();
      } catch (error: unknown) {
        if (requestId !== workspaceLoadRequestId) {
          return;
        }
        saveStatus.value = "error";
        saveMessage.value = normalizeMutationError(error, "Kunde inte ladda smarta regler.");
      }
    } finally {
      endWorkspaceTransition();
    }
  }

  async function reloadActiveWorkspace(): Promise<void> {
    if (!draft.value) {
      return;
    }
    await loadWorkspace(draft.value.id);
  }

  async function activateGroupingHistoryDraft(draftId: string): Promise<void> {
    beginWorkspaceTransition();
    try {
      saveStatus.value = "saving";
      saveMessage.value = null;
      const activatedDraft = await apiPost<PlanDraft>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${draftId}/activate`,
      );
      await loadWorkspace(activatedDraft.id);
    } finally {
      endWorkspaceTransition();
    }
  }

  async function deleteGroupingHistoryDraft(draftId: string): Promise<void> {
    beginWorkspaceTransition();
    try {
      saveStatus.value = "saving";
      saveMessage.value = null;
      await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${draftId}`);
      saveStatus.value = "saved";
      saveMessage.value = null;
    } finally {
      endWorkspaceTransition();
    }
  }

  async function activateSeatingHistoryDraft(draftId: string): Promise<void> {
    beginWorkspaceTransition();
    try {
      saveStatus.value = "saving";
      saveMessage.value = null;
      const activatedDraft = await apiPost<PlanDraft>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${draftId}/activate`,
      );
      await loadWorkspace(activatedDraft.id);
    } finally {
      endWorkspaceTransition();
    }
  }

  async function deleteSeatingHistoryDraft(draftId: string): Promise<void> {
    beginWorkspaceTransition();
    try {
      saveStatus.value = "saving";
      saveMessage.value = null;
      await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/drafts/seating/${draftId}`);
      saveStatus.value = "saved";
      saveMessage.value = null;
    } finally {
      endWorkspaceTransition();
    }
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

  async function abandonDraft(draftId?: string): Promise<void> {
    const targetDraftId = draftId ?? draft.value?.id ?? null;
    if (!targetDraftId) {
      clearWorkspace();
      return;
    }
    clearAutosaveTimer();
    saveQueued = false;
    await waitForPendingSave();
    await apiPost<PlanDraft>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${targetDraftId}/abandon`,
    );
    if (draft.value?.id === targetDraftId) {
      clearWorkspace();
    }
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
    markDirty,
  });

  return {
    draft,
    roster,
    template,
    groups,
    historyStatus,
    saveStatus,
    saveMessage,
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
    activeSeatingSmartTool,
    pendingRelationshipStudentIds,
    smartRuleFeedbackMessage,
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
    canCommitPendingRelationshipRule,
    clearWorkspace,
    resolveDraft,
    startNewGroupingDraft,
    startNewSeatingDraft,
    loadWorkspace,
    reloadActiveWorkspace,
    activateGroupingHistoryDraft,
    deleteGroupingHistoryDraft,
    activateSeatingHistoryDraft,
    deleteSeatingHistoryDraft,
    cancelPendingSave,
    flushPendingSave,
    undoGroupingDraft,
    redoGroupingDraft,
    undoSeatingDraft,
    redoSeatingDraft,
    getResumableDraft,
    getClassWorkspaceSummary,
    abandonDraft,
    setDraftSmartEnabled,
    setActiveSeatingSmartTool,
    clearPendingRelationshipSelection,
    handleSeatingSmartToolStudentSelection,
    commitPendingRelationshipRule,
    deleteRelationshipRule,
    isStudentMarkedNearTeacher,
    isStudentInPendingRelationshipSelection,
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
