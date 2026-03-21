<script setup lang="ts">
/**
 * Klassrumskartan planner root view.
 *
 * This view loads the planner catalog, keeps the top-level resumable CTA on
 * the landing screen, and switches between the class-first landing state, the
 * class workspace, and the live planner shell.
 */

import { onMounted, ref } from "vue";

import { apiGet, isApiError } from "../../api/client";
import CreateRosterModal from "./components/CreateRosterModal.vue";
import PlannerClassWorkspace from "./components/PlannerClassWorkspace.vue";
import CreateRoomTemplateModal from "./components/CreateRoomTemplateModal.vue";
import PlannerSelectionGate from "./components/PlannerSelectionGate.vue";
import PlannerWorkspaceShell from "./components/PlannerWorkspaceShell.vue";
import {
  type ClassWorkspaceSummary,
  type ResumablePlanDraft,
  type RoomTemplate,
  type Roster,
} from "./classroomPlannerTypes";
import { useClassroomState } from "./useClassroomState";

type PlannerScreen = "landing" | "class-workspace" | "planner";

const plannerState = useClassroomState();

const availableRosters = ref<Roster[]>([]);
const availableTemplates = ref<RoomTemplate[]>([]);
const selectedRosterId = ref<string | null>(null);
const selectedTemplateId = ref<string | null>(null);
const currentScreen = ref<PlannerScreen>("landing");
const plannerInitialView = ref<"groups" | "seats">("groups");
const isBootstrapping = ref(true);
const isLoadingCatalog = ref(false);
const isLoadingClassWorkspace = ref(false);
const bootstrapError = ref<string | null>(null);
const plannerActionError = ref<string | null>(null);
const resumableDraft = ref<ResumablePlanDraft | null>(null);
const classWorkspaceSummary = ref<ClassWorkspaceSummary | null>(null);
const isRosterModalOpen = ref(false);
const isTemplateModalOpen = ref(false);
const activeRosterModal = ref<Roster | null>(null);
const activeTemplateModal = ref<RoomTemplate | null>(null);

async function fetchCatalog(): Promise<void> {
  isLoadingCatalog.value = true;
  try {
    const [rosters, templates] = await Promise.all([
      apiGet<Roster[]>("/api/v1/apps/classroom.group-seating-studio/rosters"),
      apiGet<RoomTemplate[]>("/api/v1/apps/classroom.group-seating-studio/templates"),
    ]);
    availableRosters.value = rosters;
    availableTemplates.value = templates;
  } finally {
    isLoadingCatalog.value = false;
  }
}

function syncSelectionFromWorkspace(): void {
  selectedRosterId.value = plannerState.roster?.id ?? null;
  selectedTemplateId.value = plannerState.template?.id ?? null;
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

async function openClassWorkspace(rosterId: string): Promise<void> {
  plannerActionError.value = null;
  selectedRosterId.value = rosterId;
  selectedTemplateId.value = null;
  isLoadingClassWorkspace.value = true;
  try {
    classWorkspaceSummary.value = await plannerState.getClassWorkspaceSummary(rosterId);
    currentScreen.value = "class-workspace";
  } catch (error: unknown) {
    classWorkspaceSummary.value = null;
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna klassarbetsytan just nu.",
    );
  } finally {
    isLoadingClassWorkspace.value = false;
  }
}

function returnToLanding(): void {
  currentScreen.value = "landing";
  selectedRosterId.value = null;
  selectedTemplateId.value = null;
  classWorkspaceSummary.value = null;
}

async function resumeDraft(): Promise<void> {
  if (!resumableDraft.value) {
    return;
  }
  plannerActionError.value = null;
  try {
    await plannerState.resolveDraft(
      resumableDraft.value.draft.roster_id,
      resumableDraft.value.draft.template_id ?? null,
      resumableDraft.value.draft.draft_kind,
    );
    syncSelectionFromWorkspace();
    plannerInitialView.value =
      resumableDraft.value.draft.draft_kind === "seating" ? "seats" : "groups";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerState.clearWorkspace();
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte fortsätta utkastet just nu.",
    );
    console.error("Failed to resume classroom planner draft", error);
  }
}

onMounted(async () => {
  try {
    await Promise.all([
      fetchCatalog(),
      plannerState.getResumableDraft().then((draft) => {
        resumableDraft.value = draft;
      }),
    ]);
  } catch (error: unknown) {
    bootstrapError.value = error instanceof Error ? error.message : "Kunde inte ladda Klassrumskartan.";
  } finally {
    isBootstrapping.value = false;
  }
});

async function openGroupingWorkspace(): Promise<void> {
  if (!selectedRosterId.value) {
    return;
  }

  plannerActionError.value = null;
  try {
    const activeGroupingDraft = classWorkspaceSummary.value?.active_grouping_draft ?? null;
    if (activeGroupingDraft) {
      await plannerState.loadWorkspace(activeGroupingDraft.id);
    } else {
      await plannerState.resolveDraft(selectedRosterId.value, null, "grouping");
    }
    resumableDraft.value = await plannerState.getResumableDraft();
    plannerInitialView.value = "groups";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna grupparbetsytan just nu.",
    );
  }
}

async function openSeatingWorkspace(): Promise<void> {
  if (!selectedRosterId.value) {
    return;
  }

  plannerActionError.value = null;
  try {
    const activeSeatingDraft = classWorkspaceSummary.value?.active_seating_draft ?? null;
    if (activeSeatingDraft) {
      await plannerState.loadWorkspace(activeSeatingDraft.id);
    } else if (selectedTemplateId.value) {
      await plannerState.resolveDraft(selectedRosterId.value, selectedTemplateId.value, "seating");
    } else {
      return;
    }
    resumableDraft.value = await plannerState.getResumableDraft();
    plannerInitialView.value = "seats";
    currentScreen.value = "planner";
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte öppna sittplatserna just nu.",
    );
  }
}

async function resetToSelection(): Promise<void> {
  plannerActionError.value = null;
  try {
    await plannerState.abandonDraft();
    resumableDraft.value = await plannerState.getResumableDraft();
    returnToLanding();
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte lämna planeringen just nu.",
    );
  }
}

async function discardResumableDraft(): Promise<void> {
  if (!resumableDraft.value) {
    return;
  }
  plannerActionError.value = null;
  try {
    await plannerState.abandonDraft(resumableDraft.value.draft.id);
    resumableDraft.value = await plannerState.getResumableDraft();
  } catch (error: unknown) {
    plannerActionError.value = normalizeUiError(
      error,
      "Kunde inte avsluta utkastet just nu.",
    );
  }
}

function upsertRoster(roster: Roster): void {
  const next = availableRosters.value.filter((item) => item.id !== roster.id);
  availableRosters.value = [...next, roster].sort((left, right) => left.name.localeCompare(right.name, "sv"));
  selectedRosterId.value = roster.id;
  if (classWorkspaceSummary.value?.roster.id === roster.id) {
    classWorkspaceSummary.value = {
      ...classWorkspaceSummary.value,
      roster: {
        ...classWorkspaceSummary.value.roster,
        name: roster.name,
        student_count: roster.students.length,
      },
    };
  }
  isRosterModalOpen.value = false;
  activeRosterModal.value = null;
}

function deleteRoster(rosterId: string): void {
  availableRosters.value = availableRosters.value.filter((roster) => roster.id !== rosterId);
  if (selectedRosterId.value === rosterId) {
    returnToLanding();
  }
  isRosterModalOpen.value = false;
  activeRosterModal.value = null;
}

function upsertTemplate(template: RoomTemplate): void {
  const next = availableTemplates.value.filter((item) => item.id !== template.id);
  availableTemplates.value = [...next, template].sort((left, right) => left.name.localeCompare(right.name, "sv"));
  selectedTemplateId.value = template.id;
  isTemplateModalOpen.value = false;
  activeTemplateModal.value = null;
}

function deleteTemplate(templateId: string): void {
  availableTemplates.value = availableTemplates.value.filter((template) => template.id !== templateId);
  if (selectedTemplateId.value === templateId) {
    selectedTemplateId.value = null;
  }
  isTemplateModalOpen.value = false;
  activeTemplateModal.value = null;
}

function openRosterCreate(): void {
  activeRosterModal.value = null;
  isRosterModalOpen.value = true;
}

function openRosterEdit(roster: Roster): void {
  activeRosterModal.value = roster;
  isRosterModalOpen.value = true;
}

function openTemplateCreate(): void {
  activeTemplateModal.value = null;
  isTemplateModalOpen.value = true;
}

function openTemplateEdit(template: RoomTemplate): void {
  activeTemplateModal.value = template;
  isTemplateModalOpen.value = true;
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
          Börja med klassen, öppna sedan rätt arbetsyta för grupper eller sittplatser, och håll klassrummet som ett stöd där det faktiskt behövs.
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

    <PlannerSelectionGate
      v-if="!isBootstrapping && !bootstrapError && currentScreen === 'landing'"
      :available-rosters="availableRosters"
      :available-templates="availableTemplates"
      :selected-roster-id="selectedRosterId"
      :resumable-draft="resumableDraft"
      :is-loading-catalog="isLoadingCatalog"
      @select-roster="void openClassWorkspace($event)"
      @create-roster="openRosterCreate"
      @edit-roster="openRosterEdit"
      @create-template="openTemplateCreate"
      @edit-template="openTemplateEdit"
      @resume-draft="resumeDraft"
      @discard-resumable-draft="discardResumableDraft"
    />

    <PlannerClassWorkspace
      v-if="!isBootstrapping && !bootstrapError && currentScreen === 'class-workspace' && classWorkspaceSummary"
      :available-templates="availableTemplates"
      :selected-template-id="selectedTemplateId"
      :workspace-summary="classWorkspaceSummary"
      :is-loading-workspace="isLoadingClassWorkspace"
      @back-to-landing="returnToLanding"
      @select-template="selectedTemplateId = $event || null"
      @open-grouping="void openGroupingWorkspace()"
      @open-seating="void openSeatingWorkspace()"
    />

    <PlannerWorkspaceShell
      v-if="!isBootstrapping && !bootstrapError && currentScreen === 'planner'"
      :initial-view="plannerInitialView"
      @reset-selection="resetToSelection"
    />

    <CreateRosterModal
      v-if="isRosterModalOpen"
      :roster="activeRosterModal"
      @close="isRosterModalOpen = false; activeRosterModal = null"
      @saved="upsertRoster($event)"
      @deleted="deleteRoster($event)"
    />

    <CreateRoomTemplateModal
      v-if="isTemplateModalOpen"
      :template="activeTemplateModal"
      @close="isTemplateModalOpen = false; activeTemplateModal = null"
      @saved="upsertTemplate($event)"
      @deleted="deleteTemplate($event)"
    />
  </div>
</template>
