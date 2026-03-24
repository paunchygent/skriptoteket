<script setup lang="ts">
/**
 * Klassrumskartan planner root view.
 *
 * This view owns the landing-page cutover. It boots straight into the
 * overview-first workspace, keeps the planner shell separate from the home
 * surface, and routes `Avsluta` back to the teacher's trusted entry origin.
 */

import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiDelete, apiGet, isApiError } from "../../api/client";
import CreateRosterModal from "./components/CreateRosterModal.vue";
import PlannerClassWorkspace from "./components/PlannerClassWorkspace.vue";
import PlannerConfirmationDialog from "./components/PlannerConfirmationDialog.vue";
import CreateRoomTemplateModal from "./components/CreateRoomTemplateModal.vue";
import PlannerWorkspaceShell from "./components/PlannerWorkspaceShell.vue";
import {
  type ClassWorkspaceSummary,
  type RoomTemplate,
  type Roster,
} from "./classroomPlannerTypes";
import {
  type ClassroomPlannerEntryOrigin,
  isReloadNavigation,
  readClassroomPlannerEntryOriginFromHistoryState,
  resolveClassroomPlannerExitTarget,
} from "./classroomPlannerNavigation";
import { useClassroomState } from "./useClassroomState";

type PlannerScreen = "class-workspace" | "planner";

const EXIT_AUTOSAVE_TIMEOUT_MS = 1500;

const plannerState = useClassroomState();
const router = useRouter();

const availableRosters = ref<Roster[]>([]);
const availableTemplates = ref<RoomTemplate[]>([]);
const selectedRosterId = ref<string | null>(null);
const currentScreen = ref<PlannerScreen>("class-workspace");
const plannerInitialView = ref<"groups" | "seats">("groups");
const isBootstrapping = ref(true);
const isLoadingClassWorkspace = ref(false);
const bootstrapError = ref<string | null>(null);
const plannerActionError = ref<string | null>(null);
const dismissedOverviewGroupingDraftId = ref<string | null>(null);
const dismissedOverviewSeatingDraftId = ref<string | null>(null);
const classWorkspaceSummary = ref<ClassWorkspaceSummary | null>(null);
const isRosterModalOpen = ref(false);
const isTemplateModalOpen = ref(false);
const activeRosterModal = ref<Roster | null>(null);
const activeTemplateModal = ref<RoomTemplate | null>(null);
const selectedWorkspaceTemplateId = ref<string | null>(null);
const overviewDeleteRosterTarget = ref<Roster | null>(null);
const overviewDeleteTemplateTarget = ref<RoomTemplate | null>(null);
const isDeletingOverviewRoster = ref(false);
const isDeletingOverviewTemplate = ref(false);
const isSeatingLifecycleBusy = ref(false);
const busySeatingHistoryDraftId = ref<string | null>(null);
const entryOrigin = ref<ClassroomPlannerEntryOrigin | null>(null);
const isExitConfirmationOpen = ref(false);
const isExitingWithoutSave = ref(false);
const visibleOverviewGroupingDraft = computed(() => {
  const draft = classWorkspaceSummary.value?.active_grouping_draft ?? null;
  if (!draft || dismissedOverviewGroupingDraftId.value === draft.id) {
    return null;
  }
  return draft;
});
const visibleOverviewSeatingDraft = computed(() => {
  const draft = classWorkspaceSummary.value?.active_seating_draft ?? null;
  if (!draft || dismissedOverviewSeatingDraftId.value === draft.id) {
    return null;
  }
  return draft;
});

function dismissOverviewGroupingDraft(): void {
  const draftId = classWorkspaceSummary.value?.active_grouping_draft?.id ?? null;
  if (!draftId) {
    return;
  }
  dismissedOverviewGroupingDraftId.value = draftId;
}

function dismissOverviewSeatingDraft(): void {
  const draftId = classWorkspaceSummary.value?.active_seating_draft?.id ?? null;
  if (!draftId) {
    return;
  }
  dismissedOverviewSeatingDraftId.value = draftId;
}

async function fetchCatalog(): Promise<void> {
  const [rosters, templates] = await Promise.all([
    apiGet<Roster[]>("/api/v1/apps/classroom.group-seating-studio/rosters"),
    apiGet<RoomTemplate[]>("/api/v1/apps/classroom.group-seating-studio/templates"),
  ]);
  availableRosters.value = rosters;
  availableTemplates.value = templates;
}

function normalizeUiError(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message || fallbackMessage;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

async function loadClassWorkspaceSummary(rosterId: string): Promise<void> {
  classWorkspaceSummary.value = await plannerState.getClassWorkspaceSummary(rosterId);
}

function clearOverviewWorkspaceState(): void {
  selectedRosterId.value = null;
  classWorkspaceSummary.value = null;
  selectedWorkspaceTemplateId.value = null;
  dismissedOverviewGroupingDraftId.value = null;
  dismissedOverviewSeatingDraftId.value = null;
}

function resolveHomeRosterId(preferredRosterId: string | null): string | null {
  if (preferredRosterId && availableRosters.value.some((roster) => roster.id === preferredRosterId)) {
    return preferredRosterId;
  }

  if (selectedRosterId.value && availableRosters.value.some((roster) => roster.id === selectedRosterId.value)) {
    return selectedRosterId.value;
  }

  return availableRosters.value[0]?.id ?? null;
}

async function openInitialHomeWorkspace(preferredRosterId: string | null): Promise<void> {
  const nextRosterId = resolveHomeRosterId(preferredRosterId);
  if (!nextRosterId) {
    clearOverviewWorkspaceState();
    currentScreen.value = "class-workspace";
    return;
  }

  await openClassWorkspace(nextRosterId);
}

function syncWorkspaceTemplateSelection(options?: { preserveCurrent?: boolean }): void {
  const preserveCurrent = options?.preserveCurrent ?? false;
  if (
    preserveCurrent
    && selectedWorkspaceTemplateId.value
    && availableTemplates.value.some((template) => template.id === selectedWorkspaceTemplateId.value)
  ) {
    return;
  }

  const activeTemplateId = classWorkspaceSummary.value?.active_seating_draft?.template_id ?? null;
  const hasActiveTemplate =
    activeTemplateId !== null
    && availableTemplates.value.some((template) => template.id === activeTemplateId);
  selectedWorkspaceTemplateId.value = hasActiveTemplate ? activeTemplateId : null;
}

async function refreshClassWorkspaceSummaryForSelectedRoster(): Promise<void> {
  const rosterId = plannerState.roster?.id ?? selectedRosterId.value;
  if (!rosterId) {
    return;
  }
  classWorkspaceSummary.value = await plannerState.getClassWorkspaceSummary(rosterId);
  syncWorkspaceTemplateSelection({ preserveCurrent: true });
}

async function openClassWorkspace(rosterId: string): Promise<void> {
  plannerActionError.value = null;
  selectedRosterId.value = rosterId;
  dismissedOverviewGroupingDraftId.value = null;
  dismissedOverviewSeatingDraftId.value = null;
  isLoadingClassWorkspace.value = true;
  try {
    await loadClassWorkspaceSummary(rosterId);
    syncWorkspaceTemplateSelection();
    currentScreen.value = "class-workspace";
  } catch (error: unknown) {
    classWorkspaceSummary.value = null;
    selectedWorkspaceTemplateId.value = null;
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna klassarbetsytan just nu.",
    );
  } finally {
    isLoadingClassWorkspace.value = false;
  }
}

onMounted(async () => {
  try {
    entryOrigin.value = readCurrentEntryOrigin();
    const [, resumableDraft] = await Promise.all([
      fetchCatalog(),
      plannerState.getResumableDraft(),
    ]);
    await openInitialHomeWorkspace(resumableDraft?.draft.roster_id ?? null);
  } catch (error: unknown) {
    bootstrapError.value = error instanceof Error ? error.message : "Kunde inte ladda Klassrumskartan.";
  } finally {
    isBootstrapping.value = false;
  }
});

async function openGroupingWorkspace(payload: { templateId: string | null }): Promise<void> {
  if (!selectedRosterId.value) {
    return;
  }

  plannerActionError.value = null;
  try {
    const activeGroupingDraft = classWorkspaceSummary.value?.active_grouping_draft ?? null;
    if (activeGroupingDraft) {
      await plannerState.loadWorkspace(activeGroupingDraft.id);
    } else {
      await plannerState.resolveDraft(selectedRosterId.value, payload.templateId, "grouping");
    }
    await refreshClassWorkspaceSummaryForSelectedRoster();
    plannerInitialView.value = "groups";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna grupparbetsytan just nu.",
    );
  }
}

async function openSeatingWorkspace(payload: { templateId: string | null }): Promise<void> {
  if (!selectedRosterId.value) {
    return;
  }

  plannerActionError.value = null;
  try {
    const activeSeatingDraft = classWorkspaceSummary.value?.active_seating_draft ?? null;
    if (activeSeatingDraft) {
      await plannerState.loadWorkspace(activeSeatingDraft.id);
    } else {
      await plannerState.resolveDraft(selectedRosterId.value, payload.templateId, "seating");
    }
    await refreshClassWorkspaceSummaryForSelectedRoster();
    plannerInitialView.value = "seats";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna sittplatserna just nu.",
    );
  }
}

async function returnToClassWorkspace(): Promise<void> {
  const rosterId = plannerState.roster?.id ?? selectedRosterId.value;
  if (!rosterId) {
    await openInitialHomeWorkspace(null);
    return;
  }

  plannerActionError.value = null;
  try {
    await plannerState.flushPendingSave();
    if (plannerState.saveStatus === "conflict" || plannerState.saveStatus === "error") {
      plannerActionError.value =
        plannerState.saveStatus === "conflict"
          ? "Lös sparkonflikten innan du lämnar arbetsytan."
          : plannerState.saveMessage ?? "Kunde inte lämna arbetsytan just nu.";
      return;
    }
    plannerState.clearWorkspace();
    await loadClassWorkspaceSummary(rosterId);
    selectedRosterId.value = rosterId;
    syncWorkspaceTemplateSelection();
    currentScreen.value = "class-workspace";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte återvända till klassarbetsytan just nu.",
    );
  }
}

function readCurrentEntryOrigin(): ClassroomPlannerEntryOrigin | null {
  const navigationEntries = window.performance.getEntriesByType("navigation").filter(
    (entry): entry is PerformanceNavigationTiming => typeof (entry as { type?: unknown }).type === "string",
  );
  if (isReloadNavigation(navigationEntries)) {
    return null;
  }

  return readClassroomPlannerEntryOriginFromHistoryState(window.history.state);
}

async function finishExitToEntryOrigin(): Promise<void> {
  plannerState.clearWorkspace();
  clearOverviewWorkspaceState();
  currentScreen.value = "class-workspace";
  await router.replace(resolveClassroomPlannerExitTarget(entryOrigin.value));
}

async function flushPendingSaveForExit(): Promise<"saved" | "blocked" | "timed-out"> {
  if (!plannerState.draft) {
    return "saved";
  }

  const result = await Promise.race<"saved" | "blocked" | "timed-out">([
    plannerState.flushPendingSave().then((flushSucceeded) => (flushSucceeded ? "saved" : "blocked")),
    new Promise<"timed-out">((resolve) => {
      window.setTimeout(() => resolve("timed-out"), EXIT_AUTOSAVE_TIMEOUT_MS);
    }),
  ]);

  return result;
}

function closeExitConfirmation(): void {
  if (isExitingWithoutSave.value) {
    return;
  }
  isExitConfirmationOpen.value = false;
}

async function confirmExitWithoutWaiting(): Promise<void> {
  isExitingWithoutSave.value = true;
  plannerActionError.value = null;
  try {
    plannerState.cancelPendingSave();
    await finishExitToEntryOrigin();
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte lämna Klassrumskartan just nu.",
    );
  } finally {
    isExitingWithoutSave.value = false;
    isExitConfirmationOpen.value = false;
  }
}

async function exitPlannerApp(): Promise<void> {
  plannerActionError.value = null;
  try {
    const exitSaveResult = await flushPendingSaveForExit();
    if (exitSaveResult === "blocked") {
      plannerActionError.value =
        plannerState.saveStatus === "conflict"
          ? "Lös sparkonflikten innan du avslutar Klassrumskartan."
          : plannerState.saveMessage ?? "Kunde inte avsluta Klassrumskartan just nu.";
      return;
    }

    if (exitSaveResult === "timed-out") {
      isExitConfirmationOpen.value = true;
      return;
    }

    await finishExitToEntryOrigin();
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte lämna Klassrumskartan just nu.",
    );
  }
}

async function changeSeatingTemplate(payload: { templateId: string | null }): Promise<void> {
  const rosterId = plannerState.roster?.id ?? selectedRosterId.value;
  if (!rosterId) {
    return;
  }

  plannerActionError.value = null;
  try {
    await plannerState.flushPendingSave();
    if (plannerState.saveStatus === "conflict" || plannerState.saveStatus === "error") {
      plannerActionError.value =
        plannerState.saveStatus === "conflict"
          ? "Lös sparkonflikten innan du byter klassrum."
          : plannerState.saveMessage ?? "Kunde inte spara ändringarna innan klassrummet byttes.";
      return;
    }
    await plannerState.resolveDraft(rosterId, payload.templateId, "seating");
    plannerInitialView.value = "seats";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte byta klassrum för sittplatserna just nu.",
    );
  }
}

async function changeGroupingTemplate(payload: { templateId: string | null }): Promise<void> {
  const rosterId = plannerState.roster?.id ?? selectedRosterId.value;
  if (!rosterId) {
    return;
  }

  plannerActionError.value = null;
  try {
    await plannerState.flushPendingSave();
    if (plannerState.saveStatus === "conflict" || plannerState.saveStatus === "error") {
      plannerActionError.value =
        plannerState.saveStatus === "conflict"
          ? "Lös sparkonflikten innan du byter gruppkontext."
          : plannerState.saveMessage ?? "Kunde inte spara ändringarna innan gruppkontexten byttes.";
      return;
    }
    await plannerState.resolveDraft(rosterId, payload.templateId, "grouping");
    plannerInitialView.value = "groups";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte uppdatera gruppkontexten just nu.",
    );
  }
}

async function startNewGroupingDraft(payload: { templateId: string | null }): Promise<void> {
  const rosterId = plannerState.roster?.id ?? selectedRosterId.value;
  if (!rosterId) {
    return;
  }

  plannerActionError.value = null;
  try {
    await plannerState.flushPendingSave();
    if (plannerState.saveStatus === "conflict" || plannerState.saveStatus === "error") {
      plannerActionError.value =
        plannerState.saveStatus === "conflict"
          ? "Lös sparkonflikten innan du startar ett nytt grupputkast."
          : plannerState.saveMessage ?? "Kunde inte spara ändringarna innan nytt grupputkast startades.";
      return;
    }
    await plannerState.startNewGroupingDraft(rosterId, payload.templateId);
    await refreshClassWorkspaceSummaryForSelectedRoster();
    plannerInitialView.value = "groups";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte starta ett nytt grupputkast just nu.",
    );
  }
}

async function startNewSeatingDraft(payload: { templateId: string }): Promise<void> {
  const rosterId = plannerState.roster?.id ?? selectedRosterId.value;
  if (!rosterId || isSeatingLifecycleBusy.value) {
    return;
  }

  plannerActionError.value = null;
  isSeatingLifecycleBusy.value = true;
  try {
    await plannerState.flushPendingSave();
    if (plannerState.saveStatus === "conflict" || plannerState.saveStatus === "error") {
      plannerActionError.value =
        plannerState.saveStatus === "conflict"
          ? "Lös sparkonflikten innan du startar ett nytt sittschema."
          : plannerState.saveMessage ?? "Kunde inte spara ändringarna innan nytt sittschema startades.";
      return;
    }
    await plannerState.startNewSeatingDraft(rosterId, payload.templateId);
    await refreshClassWorkspaceSummaryForSelectedRoster();
    plannerInitialView.value = "seats";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte starta ett nytt sittschema just nu.",
    );
  } finally {
    isSeatingLifecycleBusy.value = false;
  }
}

async function openGroupingHistoryDraft(draftId: string): Promise<void> {
  plannerActionError.value = null;
  try {
    await plannerState.activateGroupingHistoryDraft(draftId);
    await refreshClassWorkspaceSummaryForSelectedRoster();
    plannerInitialView.value = "groups";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna det historiska grupputkastet just nu.",
    );
  }
}

async function openSeatingHistoryDraft(draftId: string): Promise<void> {
  if (isSeatingLifecycleBusy.value) {
    return;
  }
  plannerActionError.value = null;
  isSeatingLifecycleBusy.value = true;
  busySeatingHistoryDraftId.value = draftId;
  try {
    await plannerState.activateSeatingHistoryDraft(draftId);
    await refreshClassWorkspaceSummaryForSelectedRoster();
    plannerInitialView.value = "seats";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna det historiska sittschemat just nu.",
    );
  } finally {
    busySeatingHistoryDraftId.value = null;
    isSeatingLifecycleBusy.value = false;
  }
}

async function deleteGroupingHistoryDraft(draftId: string): Promise<void> {
  const rosterId = selectedRosterId.value ?? classWorkspaceSummary.value?.roster.id ?? null;
  if (!rosterId) {
    return;
  }

  plannerActionError.value = null;
  try {
    await plannerState.deleteGroupingHistoryDraft(draftId);
    await loadClassWorkspaceSummary(rosterId);
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte ta bort det historiska grupputkastet just nu.",
    );
  }
}

async function deleteSeatingHistoryDraft(draftId: string): Promise<void> {
  const rosterId = selectedRosterId.value ?? classWorkspaceSummary.value?.roster.id ?? null;
  if (!rosterId || isSeatingLifecycleBusy.value) {
    return;
  }

  plannerActionError.value = null;
  isSeatingLifecycleBusy.value = true;
  busySeatingHistoryDraftId.value = draftId;
  try {
    await plannerState.deleteSeatingHistoryDraft(draftId);
    await loadClassWorkspaceSummary(rosterId);
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte ta bort det historiska sittschemat just nu.",
    );
  } finally {
    busySeatingHistoryDraftId.value = null;
    isSeatingLifecycleBusy.value = false;
  }
}

async function selectPlannerWorkspaceMode(mode: "overview" | "grouping" | "seating"): Promise<void> {
  if (mode === "overview") {
    await returnToClassWorkspace();
    return;
  }

  if (plannerState.draft) {
    plannerActionError.value = null;
    await plannerState.flushPendingSave();
    if (plannerState.saveStatus === "conflict" || plannerState.saveStatus === "error") {
      plannerActionError.value =
        plannerState.saveStatus === "conflict"
          ? "Lös sparkonflikten innan du byter arbetsyta."
          : plannerState.saveMessage ?? "Kunde inte byta arbetsyta just nu.";
      return;
    }
  }

  if (mode === "grouping") {
    await openGroupingWorkspace({ templateId: null });
    return;
  }

  await openSeatingWorkspace({ templateId: null });
}

async function upsertRoster(roster: Roster): Promise<void> {
  const wasCreatingRoster = activeRosterModal.value === null;
  const wasEditingCurrentRoster = activeRosterModal.value?.id === classWorkspaceSummary.value?.roster.id;
  const next = availableRosters.value.filter((item) => item.id !== roster.id);
  availableRosters.value = [...next, roster].sort((left, right) => left.name.localeCompare(right.name, "sv"));
  if (wasEditingCurrentRoster && classWorkspaceSummary.value) {
    classWorkspaceSummary.value = {
      ...classWorkspaceSummary.value,
      roster: {
        ...classWorkspaceSummary.value.roster,
        name: roster.name,
        student_count: roster.students.length,
      },
    };
    selectedRosterId.value = roster.id;
  } else if (currentScreen.value !== "class-workspace") {
    selectedRosterId.value = roster.id;
  }
  isRosterModalOpen.value = false;
  activeRosterModal.value = null;

  if (currentScreen.value === "class-workspace" && wasCreatingRoster) {
    await openClassWorkspace(roster.id);
  }
}

function deleteRoster(rosterId: string): void {
  availableRosters.value = availableRosters.value.filter((roster) => roster.id !== rosterId);
  if (selectedRosterId.value === rosterId) {
    void openInitialHomeWorkspace(null);
  }
  isRosterModalOpen.value = false;
  activeRosterModal.value = null;
}

function closeOverviewRosterDelete(): void {
  if (isDeletingOverviewRoster.value) {
    return;
  }
  overviewDeleteRosterTarget.value = null;
}

function upsertTemplate(template: RoomTemplate): void {
  const next = availableTemplates.value.filter((item) => item.id !== template.id);
  availableTemplates.value = [...next, template].sort((left, right) => left.name.localeCompare(right.name, "sv"));
  selectedWorkspaceTemplateId.value = template.id;
  isTemplateModalOpen.value = false;
  activeTemplateModal.value = null;
}

function deleteTemplate(templateId: string): void {
  availableTemplates.value = availableTemplates.value.filter((template) => template.id !== templateId);
  if (selectedWorkspaceTemplateId.value === templateId) {
    selectedWorkspaceTemplateId.value = null;
    syncWorkspaceTemplateSelection();
  }
  isTemplateModalOpen.value = false;
  activeTemplateModal.value = null;
}

function closeOverviewTemplateDelete(): void {
  if (isDeletingOverviewTemplate.value) {
    return;
  }
  overviewDeleteTemplateTarget.value = null;
}

function openRosterCreate(): void {
  activeRosterModal.value = null;
  isRosterModalOpen.value = true;
}

function openRosterEdit(roster: Roster): void {
  activeRosterModal.value = roster;
  isRosterModalOpen.value = true;
}

function openSelectedRosterEdit(): void {
  const activeRoster = availableRosters.value.find((roster) => roster.id === selectedRosterId.value) ?? null;
  if (!activeRoster) {
    return;
  }
  openRosterEdit(activeRoster);
}

function openSelectedRosterDelete(): void {
  const selectedRoster = availableRosters.value.find((roster) => roster.id === selectedRosterId.value) ?? null;
  if (!selectedRoster) {
    return;
  }
  overviewDeleteRosterTarget.value = selectedRoster;
}

function openTemplateCreate(): void {
  activeTemplateModal.value = null;
  isTemplateModalOpen.value = true;
}

function openTemplateEdit(template: RoomTemplate): void {
  activeTemplateModal.value = template;
  isTemplateModalOpen.value = true;
}

function selectWorkspaceRoster(rosterId: string): void {
  if (rosterId === selectedRosterId.value) {
    return;
  }
  void openClassWorkspace(rosterId);
}

function selectWorkspaceTemplate(templateId: string | null): void {
  selectedWorkspaceTemplateId.value = templateId;
}

function openSelectedTemplateEdit(): void {
  const selectedTemplate = availableTemplates.value.find(
    (template) => template.id === selectedWorkspaceTemplateId.value,
  );
  if (!selectedTemplate) {
    return;
  }
  openTemplateEdit(selectedTemplate);
}

function openOverviewTemplateEdit(template?: RoomTemplate): void {
  if (template) {
    openTemplateEdit(template);
    return;
  }
  openSelectedTemplateEdit();
}

function openSelectedTemplateDelete(): void {
  const selectedTemplate = availableTemplates.value.find(
    (template) => template.id === selectedWorkspaceTemplateId.value,
  );
  if (!selectedTemplate) {
    return;
  }
  overviewDeleteTemplateTarget.value = selectedTemplate;
}

async function confirmOverviewTemplateDelete(): Promise<void> {
  if (!overviewDeleteTemplateTarget.value) {
    return;
  }

  isDeletingOverviewTemplate.value = true;
  plannerActionError.value = null;
  try {
    await apiDelete<void>(
      `/api/v1/apps/classroom.group-seating-studio/templates/${overviewDeleteTemplateTarget.value.id}`,
    );
    deleteTemplate(overviewDeleteTemplateTarget.value.id);
    overviewDeleteTemplateTarget.value = null;
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte ta bort klassrummet just nu.",
    );
  } finally {
    isDeletingOverviewTemplate.value = false;
  }
}

async function confirmOverviewRosterDelete(): Promise<void> {
  if (!overviewDeleteRosterTarget.value) {
    return;
  }

  isDeletingOverviewRoster.value = true;
  plannerActionError.value = null;
  try {
    await apiDelete<void>(
      `/api/v1/apps/classroom.group-seating-studio/rosters/${overviewDeleteRosterTarget.value.id}`,
    );
    deleteRoster(overviewDeleteRosterTarget.value.id);
    overviewDeleteRosterTarget.value = null;
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte ta bort klasslistan just nu.",
    );
  } finally {
    isDeletingOverviewRoster.value = false;
  }
}
</script>

<template>
  <div class="mx-auto max-w-[90rem] space-y-6 px-4 py-4 md:px-6">
    <header class="border-b border-navy pb-4">
      <div class="space-y-1">
        <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Curated App
        </p>
        <h1 class="font-serif text-4xl text-navy md:text-5xl">
          Klassrumskartan
        </h1>
        <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
          Arbeta vidare från översikten och öppna grupper eller sittplatser när du behöver dem.
        </p>
      </div>
    </header>

    <div
      v-if="isBootstrapping"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      Laddar planeringsmiljön...
    </div>

    <div
      v-else-if="bootstrapError"
      class="system-message system-message-error"
    >
      <div class="system-message-content">
        {{ bootstrapError }}
      </div>
    </div>

    <div
      v-else-if="plannerActionError"
      class="system-message system-message-error"
    >
      <div class="system-message-content">
        {{ plannerActionError }}
      </div>
    </div>

    <PlannerClassWorkspace
      v-if="!isBootstrapping && !bootstrapError && currentScreen === 'class-workspace'"
      :key="classWorkspaceSummary?.roster.id ?? 'empty-overview'"
      :workspace-summary="classWorkspaceSummary"
      :available-rosters="availableRosters"
      :available-templates="availableTemplates"
      :selected-roster-id="selectedRosterId"
      :selected-template-id="selectedWorkspaceTemplateId"
      :is-loading-workspace="isLoadingClassWorkspace"
      :visible-grouping-draft="visibleOverviewGroupingDraft"
      :visible-seating-draft="visibleOverviewSeatingDraft"
      @exit-app="void exitPlannerApp()"
      @create-roster="openRosterCreate"
      @edit-roster="openSelectedRosterEdit"
      @delete-current-roster="openSelectedRosterDelete"
      @select-roster="selectWorkspaceRoster"
      @create-template="openTemplateCreate"
      @select-template="selectWorkspaceTemplate"
      @edit-current-template="openOverviewTemplateEdit"
      @delete-current-template="openSelectedTemplateDelete"
      @open-grouping="void openGroupingWorkspace($event)"
      @open-seating="void openSeatingWorkspace($event)"
      @dismiss-grouping-draft="dismissOverviewGroupingDraft"
      @dismiss-seating-draft="dismissOverviewSeatingDraft"
    />

    <PlannerWorkspaceShell
      v-if="!isBootstrapping && !bootstrapError && currentScreen === 'planner'"
      :available-templates="availableTemplates"
      :initial-view="plannerInitialView"
      :workspace-summary="classWorkspaceSummary"
      :seating-lifecycle-busy="isSeatingLifecycleBusy"
      :seating-history-busy-draft-id="busySeatingHistoryDraftId"
      @change-grouping-template="void changeGroupingTemplate($event)"
      @change-seating-template="void changeSeatingTemplate($event)"
      @new-grouping-draft="void startNewGroupingDraft($event)"
      @new-seating-draft="void startNewSeatingDraft($event)"
      @edit-roster="openSelectedRosterEdit"
      @open-grouping-history-draft="void openGroupingHistoryDraft($event)"
      @delete-grouping-history-draft="void deleteGroupingHistoryDraft($event)"
      @open-seating-history-draft="void openSeatingHistoryDraft($event)"
      @delete-seating-history-draft="void deleteSeatingHistoryDraft($event)"
      @edit-current-template="openTemplateEdit"
      @select-workspace-mode="void selectPlannerWorkspaceMode($event)"
      @exit-app="void exitPlannerApp()"
    />

    <CreateRosterModal
      v-if="isRosterModalOpen"
      :roster="activeRosterModal"
      @close="isRosterModalOpen = false; activeRosterModal = null"
      @saved="void upsertRoster($event)"
      @deleted="deleteRoster($event)"
    />

    <CreateRoomTemplateModal
      v-if="isTemplateModalOpen"
      :template="activeTemplateModal"
      @close="isTemplateModalOpen = false; activeTemplateModal = null"
      @saved="upsertTemplate($event)"
      @deleted="deleteTemplate($event)"
    />

    <PlannerConfirmationDialog
      v-if="overviewDeleteRosterTarget"
      eyebrow="Ta bort klasslista"
      title="Är du säker?"
      :message="`Klasslistan ${overviewDeleteRosterTarget.name} tas bort från översikten. Aktiva utkast som fortfarande använder klassen skyddas av backend-reglerna och kan stoppa borttagningen.`"
      confirm-label="Ta bort klasslista"
      :is-submitting="isDeletingOverviewRoster"
      @cancel="closeOverviewRosterDelete"
      @confirm="void confirmOverviewRosterDelete()"
    />

    <PlannerConfirmationDialog
      v-if="overviewDeleteTemplateTarget"
      eyebrow="Ta bort klassrum"
      title="Är du säker?"
      :message="`Klassrummet ${overviewDeleteTemplateTarget.name} tas bort från översikten. Utkast som fortfarande använder klassrummet skyddas av backend-reglerna och kan stoppa borttagningen.`"
      confirm-label="Ta bort klassrum"
      :is-submitting="isDeletingOverviewTemplate"
      @cancel="closeOverviewTemplateDelete"
      @confirm="void confirmOverviewTemplateDelete()"
    />

    <PlannerConfirmationDialog
      v-if="isExitConfirmationOpen"
      eyebrow="Avsluta"
      title="Lämna Klassrumskartan?"
      message="Den senaste autosparningen blev inte klar i tid. Om du lämnar nu kan de senaste ändringarna gå förlorade."
      confirm-label="Avsluta ändå"
      :is-submitting="isExitingWithoutSave"
      @cancel="closeExitConfirmation"
      @confirm="void confirmExitWithoutWaiting()"
    />
  </div>
</template>
