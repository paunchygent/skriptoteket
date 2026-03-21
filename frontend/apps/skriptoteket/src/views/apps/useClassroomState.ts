/**
 * Classroom planner Pinia store.
 *
 * This store owns the mutable Klassrumskartan draft workspace used by the
 * planner SPA. It hydrates the backend workspace contract, exposes normalized
 * lookup maps for the drag-and-drop UI, schedules optimistic autosave patches,
 * and coordinates validation, suggestions, randomization, and snapshot
 * finalization without duplicating the backend rule engine in TypeScript.
 */

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { ApiError, apiGet, apiPatch, apiPost, isApiError } from "../../api/client";
import {
  CLASSROOM_PLANNER_DRAFT_SESSION_KEY,
  defaultPlanningProfile,
  type ArrangementSnapshot,
  type DraftGroup,
  type DraftWorkspaceResponse,
  type GroupAssignment,
  type PairConstraint,
  type PlanDraft,
  type PlanningProfile,
  type RoomTemplate,
  type Roster,
  type SaveStatus,
  type SeatAssignment,
  type Student,
  type StudentPlanningMeta,
  type SuggestionPlan,
  type SuggestionListResponse,
  type ValidationFinding,
  type ValidationResultResponse,
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

export const useClassroomState = defineStore("classroom-state", () => {
  const draft = ref<PlanDraft | null>(null);
  const roster = ref<Roster | null>(null);
  const template = ref<RoomTemplate | null>(null);
  const groups = ref<DraftGroup[]>([]);
  const groupAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const seatAssignmentsByStudentId = ref<Record<string, string | null>>({});
  const studentPlanningMetaByStudentId = ref<Record<string, StudentPlanningMeta>>({});
  const pairConstraints = ref<PairConstraint[]>([]);
  const planningProfile = ref<PlanningProfile>(defaultPlanningProfile());
  const validationFindings = ref<ValidationFinding[]>([]);
  const suggestions = ref<SuggestionPlan[]>([]);
  const snapshots = ref<ArrangementSnapshot[]>([]);
  const saveStatus = ref<SaveStatus>("idle");
  const saveMessage = ref<string | null>(null);

  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
  let saveInFlight = false;
  let saveQueued = false;

  const hasWorkspace = computed(() => {
    return draft.value !== null && roster.value !== null && template.value !== null;
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

  const hardFindings = computed(() =>
    validationFindings.value.filter((finding) => finding.severity === "hard"),
  );

  const softFindings = computed(() =>
    validationFindings.value.filter((finding) => finding.severity === "soft"),
  );

  function clearAutosaveTimer(): void {
    if (autosaveTimer) {
      clearTimeout(autosaveTimer);
      autosaveTimer = null;
    }
  }

  function storeDraftId(draftId: string | null): void {
    if (draftId) {
      sessionStorage.setItem(CLASSROOM_PLANNER_DRAFT_SESSION_KEY, draftId);
      return;
    }
    sessionStorage.removeItem(CLASSROOM_PLANNER_DRAFT_SESSION_KEY);
  }

  function resetTransientPanels(): void {
    validationFindings.value = [];
    suggestions.value = [];
  }

  function markDirty(): void {
    resetTransientPanels();
    scheduleAutosave();
  }

  function applyWorkspace(workspace: DraftWorkspaceResponse): void {
    draft.value = workspace.draft;
    roster.value = workspace.roster;
    template.value = workspace.template;
    groups.value = reindexGroups(workspace.groups);
    groupAssignmentsByStudentId.value = normalizeAssignments(workspace.group_assignments, "group_id");
    seatAssignmentsByStudentId.value = normalizeAssignments(workspace.seat_assignments, "seat_id");
    studentPlanningMetaByStudentId.value = Object.fromEntries(
      workspace.student_planning_meta.map((meta) => [meta.student_id, meta]),
    );
    pairConstraints.value = [...workspace.pair_constraints];
    planningProfile.value = workspace.planning_profile;
    validationFindings.value = [];
    suggestions.value = [];
    saveStatus.value = "saved";
    saveMessage.value = null;
    storeDraftId(workspace.draft.id);
  }

  function serializeWorkspacePatch(): Record<string, unknown> {
    return {
      expected_revision: draft.value?.revision ?? null,
      groups: groups.value,
      group_assignments: groupAssignments.value,
      seat_assignments: seatAssignments.value,
      student_planning_meta: studentPlanningMeta.value,
      pair_constraints: pairConstraints.value,
      planning_profile: planningProfile.value,
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

  async function persistWorkspace(): Promise<void> {
    if (!draft.value) {
      return;
    }
    if (saveInFlight) {
      saveQueued = true;
      return;
    }

    saveInFlight = true;
    try {
      const updatedDraft = await apiPatch<PlanDraft>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}`,
        serializeWorkspacePatch(),
      );
      draft.value = updatedDraft;
      saveStatus.value = "saved";
      saveMessage.value = null;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 409) {
        saveStatus.value = "conflict";
        saveMessage.value = "Utkastet har ändrats i en annan flik. Ladda om arbetsytan innan du fortsätter.";
      } else {
        saveStatus.value = "error";
        saveMessage.value = normalizeMutationError(error, "Kunde inte spara planeringen.");
      }
    } finally {
      saveInFlight = false;
      if (saveQueued && saveStatus.value !== "conflict") {
        saveQueued = false;
        await persistWorkspace();
      }
    }
  }

  function scheduleAutosave(): void {
    if (!draft.value) {
      return;
    }
    clearAutosaveTimer();
    saveStatus.value = "saving";
    autosaveTimer = setTimeout(() => {
      void persistWorkspace();
    }, AUTOSAVE_DELAY_MS);
  }

  function clearWorkspace(): void {
    clearAutosaveTimer();
    draft.value = null;
    roster.value = null;
    template.value = null;
    groups.value = [];
    groupAssignmentsByStudentId.value = {};
    seatAssignmentsByStudentId.value = {};
    studentPlanningMetaByStudentId.value = {};
    pairConstraints.value = [];
    planningProfile.value = defaultPlanningProfile();
    validationFindings.value = [];
    suggestions.value = [];
    snapshots.value = [];
    saveStatus.value = "idle";
    saveMessage.value = null;
    storeDraftId(null);
  }

  async function createDraft(rosterId: string, templateId: string, lessonModeId: string): Promise<void> {
    saveStatus.value = "saving";
    saveMessage.value = null;
    const newDraft = await apiPost<PlanDraft>("/api/v1/apps/classroom.group-seating-studio/drafts", {
      roster_id: rosterId,
      template_id: templateId,
      lesson_mode_id: lessonModeId,
    });
    await loadWorkspace(newDraft.id);
  }

  async function loadWorkspace(draftId: string): Promise<void> {
    const workspace = await apiGet<DraftWorkspaceResponse>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${draftId}/workspace`,
    );
    applyWorkspace(workspace);
  }

  async function reloadActiveWorkspace(): Promise<void> {
    if (!draft.value) {
      return;
    }
    await loadWorkspace(draft.value.id);
  }

  function getStoredDraftId(): string | null {
    return sessionStorage.getItem(CLASSROOM_PLANNER_DRAFT_SESSION_KEY);
  }

  const {
    assignStudentToGroup,
    removeStudentFromGroup,
    assignStudentToSeat,
    swapSeatAssignments,
    clearSeatAssignment,
    addGroup,
    renameGroup,
    moveGroup,
    removeGroup,
    updatePlanningProfile,
    setStudentPlanningMeta,
    resetStudentPlanningMeta,
    setPairConstraint,
  } = createPlannerMutationActions({
    studentsById,
    seatsById,
    groupsById,
    groups,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    studentPlanningMetaByStudentId,
    pairConstraints,
    planningProfile,
    markDirty,
  });

  async function validateDraft(): Promise<ValidationFinding[]> {
    if (!draft.value) {
      return [];
    }
    const result = await apiPost<ValidationResultResponse>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}/validate`,
    );
    validationFindings.value = result.findings;
    return result.findings;
  }

  async function loadSuggestions(): Promise<SuggestionPlan[]> {
    if (!draft.value) {
      return [];
    }
    const result = await apiPost<SuggestionListResponse>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}/suggestions`,
    );
    suggestions.value = result.suggestions;
    return result.suggestions;
  }

  async function applySuggestion(suggestionId: string): Promise<void> {
    if (!draft.value) {
      return;
    }
    const response = await apiPost<PlanDraft>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}/suggestions/${suggestionId}/apply`,
      { expected_revision: draft.value.revision },
    );
    draft.value = response;
    const selectedSuggestion = suggestions.value.find(
      (suggestion) => suggestion.suggestion_id === suggestionId,
    );
    if (selectedSuggestion) {
      groups.value = reindexGroups(selectedSuggestion.groups);
      groupAssignmentsByStudentId.value = normalizeAssignments(
        selectedSuggestion.group_assignments,
        "group_id",
      );
      seatAssignmentsByStudentId.value = normalizeAssignments(
        selectedSuggestion.seat_assignments,
        "seat_id",
      );
      validationFindings.value = selectedSuggestion.findings;
    } else {
      await reloadActiveWorkspace();
    }
    saveStatus.value = "saved";
    saveMessage.value = null;
  }

  async function randomizeDraft(): Promise<void> {
    if (!draft.value) {
      return;
    }
    const response = await apiPost<PlanDraft>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}/randomize`,
      { expected_revision: draft.value.revision },
    );
    draft.value = response;
    await reloadActiveWorkspace();
  }

  async function finalizeDraft(): Promise<ArrangementSnapshot> {
    if (!draft.value) {
      throw new Error("Det finns inget aktivt utkast att fastställa.");
    }
    const snapshot = await apiPost<ArrangementSnapshot>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${draft.value.id}/finalize`,
    );
    snapshots.value = [snapshot, ...snapshots.value.filter((entry) => entry.id !== snapshot.id)];
    return snapshot;
  }

  async function loadSnapshots(): Promise<ArrangementSnapshot[]> {
    const result = await apiGet<ArrangementSnapshot[]>(
      "/api/v1/apps/classroom.group-seating-studio/snapshots",
    );
    snapshots.value = result;
    return result;
  }

  return {
    draft,
    roster,
    template,
    groups,
    pairConstraints,
    planningProfile,
    validationFindings,
    suggestions,
    snapshots,
    saveStatus,
    saveMessage,
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
    studentPlanningMeta,
    groupAssignments,
    seatAssignments,
    ungroupedStudents,
    unseatedStudents,
    studentsByGroupId,
    studentBySeatId,
    zones,
    hardFindings,
    softFindings,
    getStoredDraftId,
    clearWorkspace,
    createDraft,
    loadWorkspace,
    reloadActiveWorkspace,
    assignStudentToGroup,
    removeStudentFromGroup,
    assignStudentToSeat,
    swapSeatAssignments,
    clearSeatAssignment,
    addGroup,
    renameGroup,
    moveGroup,
    removeGroup,
    updatePlanningProfile,
    setStudentPlanningMeta,
    resetStudentPlanningMeta,
    setPairConstraint,
    validateDraft,
    loadSuggestions,
    applySuggestion,
    randomizeDraft,
    finalizeDraft,
    loadSnapshots,
  };
});
