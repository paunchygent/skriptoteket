<script setup lang="ts">
/**
 * Klassrumskartan planner root view.
 *
 * This view bootstraps the classroom planner, hydrates reusable catalog assets,
 * restores the active draft when available, and switches between the selection
 * gate and the live Slice 2 workspace shell.
 */

import { computed, onMounted, ref } from "vue";

import { apiGet } from "../../api/client";
import CreateRosterModal from "./components/CreateRosterModal.vue";
import CreateRoomTemplateModal from "./components/CreateRoomTemplateModal.vue";
import PlannerSelectionGate from "./components/PlannerSelectionGate.vue";
import PlannerWorkspaceShell from "./components/PlannerWorkspaceShell.vue";
import {
  type LessonMode,
  type PlannerBootstrapResponse,
  type RoomTemplate,
  type Roster,
} from "./classroomPlannerTypes";
import { useClassroomState } from "./useClassroomState";

const plannerState = useClassroomState();

const lessonModes = ref<LessonMode[]>([]);
const availableRosters = ref<Roster[]>([]);
const availableTemplates = ref<RoomTemplate[]>([]);
const selectedLessonModeId = ref<string | null>(null);
const selectedRosterId = ref<string | null>(null);
const selectedTemplateId = ref<string | null>(null);
const isBootstrapping = ref(true);
const isLoadingCatalog = ref(false);
const bootstrapError = ref<string | null>(null);
const isPlannerOpen = ref(false);
const isRosterModalOpen = ref(false);
const isTemplateModalOpen = ref(false);
const activeRosterModal = ref<Roster | null>(null);
const activeTemplateModal = ref<RoomTemplate | null>(null);

const selectedLessonMode = computed(() => {
  return lessonModes.value.find((mode) => mode.id === selectedLessonModeId.value) ?? null;
});

const selectedRoster = computed(() => {
  return availableRosters.value.find((roster) => roster.id === selectedRosterId.value) ?? null;
});

const selectedTemplate = computed(() => {
  return availableTemplates.value.find((template) => template.id === selectedTemplateId.value) ?? null;
});

const canStartPlanning = computed(() => {
  return Boolean(selectedLessonMode.value && selectedRoster.value && selectedTemplate.value);
});

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
  selectedLessonModeId.value = plannerState.draft?.lesson_mode_id ?? null;
}

async function resumeDraft(draftId: string): Promise<void> {
  try {
    await plannerState.loadWorkspace(draftId);
    syncSelectionFromWorkspace();
    isPlannerOpen.value = true;
  } catch (error: unknown) {
    plannerState.clearWorkspace();
    console.error("Failed to resume classroom planner draft", error);
  }
}

onMounted(async () => {
  try {
    const bootstrap = await apiGet<PlannerBootstrapResponse>(
      "/api/v1/apps/classroom.group-seating-studio/bootstrap",
    );
    lessonModes.value = bootstrap.lesson_modes;
    await fetchCatalog();

    const storedDraftId = plannerState.getStoredDraftId();
    if (storedDraftId) {
      await resumeDraft(storedDraftId);
    }
  } catch (error: unknown) {
    bootstrapError.value = error instanceof Error ? error.message : "Kunde inte ladda Klassrumskartan.";
  } finally {
    isBootstrapping.value = false;
  }
});

async function startPlanning(): Promise<void> {
  if (!selectedRoster.value || !selectedTemplate.value || !selectedLessonMode.value) {
    return;
  }

  await plannerState.createDraft(
    selectedRoster.value.id,
    selectedTemplate.value.id,
    selectedLessonMode.value.id,
  );
  isPlannerOpen.value = true;
}

function resetToSelection(): void {
  isPlannerOpen.value = false;
  plannerState.clearWorkspace();
}

function upsertRoster(roster: Roster): void {
  const next = availableRosters.value.filter((item) => item.id !== roster.id);
  availableRosters.value = [...next, roster].sort((left, right) => left.name.localeCompare(right.name, "sv"));
  selectedRosterId.value = roster.id;
  isRosterModalOpen.value = false;
  activeRosterModal.value = null;
}

function deleteRoster(rosterId: string): void {
  availableRosters.value = availableRosters.value.filter((roster) => roster.id !== rosterId);
  if (selectedRosterId.value === rosterId) {
    selectedRosterId.value = null;
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
          Planera grupper och sittplatser, slumpa fram en första version, och bygg vidare med regler som kan togglas på eller av när den regelstyrda motorn växer i kommande stories.
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

    <PlannerSelectionGate
      v-else-if="!isPlannerOpen"
      :lesson-modes="lessonModes"
      :available-rosters="availableRosters"
      :available-templates="availableTemplates"
      :selected-lesson-mode-id="selectedLessonModeId"
      :selected-roster-id="selectedRosterId"
      :selected-template-id="selectedTemplateId"
      :is-loading-catalog="isLoadingCatalog"
      :can-start-planning="canStartPlanning"
      @select-lesson-mode="selectedLessonModeId = $event"
      @select-roster="selectedRosterId = $event"
      @select-template="selectedTemplateId = $event"
      @create-roster="openRosterCreate"
      @edit-roster="openRosterEdit"
      @create-template="openTemplateCreate"
      @edit-template="openTemplateEdit"
      @start-planning="startPlanning"
    />

    <PlannerWorkspaceShell
      v-else
      :selected-lesson-mode-name="selectedLessonMode?.name ?? plannerState.draft?.lesson_mode_id ?? ''"
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
