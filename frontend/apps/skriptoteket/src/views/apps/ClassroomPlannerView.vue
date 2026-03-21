<script setup lang="ts">
/**
 * Klassrumskartan planner root view.
 *
 * This view bootstraps the classroom planner, hydrates reusable catalog assets,
 * offers an explicit resume CTA for the current active draft, and switches
 * between the selection gate and the live planner workspace shell.
 */

import { computed, onMounted, ref } from "vue";

import { apiGet } from "../../api/client";
import CreateRosterModal from "./components/CreateRosterModal.vue";
import CreateRoomTemplateModal from "./components/CreateRoomTemplateModal.vue";
import PlannerSelectionGate from "./components/PlannerSelectionGate.vue";
import PlannerWorkspaceShell from "./components/PlannerWorkspaceShell.vue";
import {
  type PlannerBootstrapResponse,
  type ResumablePlanDraft,
  type RoomTemplate,
  type Roster,
} from "./classroomPlannerTypes";
import { useClassroomState } from "./useClassroomState";

const plannerState = useClassroomState();

const availableRosters = ref<Roster[]>([]);
const availableTemplates = ref<RoomTemplate[]>([]);
const selectedRosterId = ref<string | null>(null);
const selectedTemplateId = ref<string | null>(null);
const isBootstrapping = ref(true);
const isLoadingCatalog = ref(false);
const bootstrapError = ref<string | null>(null);
const plannerActionError = ref<string | null>(null);
const resumableDraft = ref<ResumablePlanDraft | null>(null);
const isPlannerOpen = ref(false);
const isRosterModalOpen = ref(false);
const isTemplateModalOpen = ref(false);
const activeRosterModal = ref<Roster | null>(null);
const activeTemplateModal = ref<RoomTemplate | null>(null);

const selectedRoster = computed(() => {
  return availableRosters.value.find((roster) => roster.id === selectedRosterId.value) ?? null;
});

const selectedTemplate = computed(() => {
  return availableTemplates.value.find((template) => template.id === selectedTemplateId.value) ?? null;
});

const canStartPlanning = computed(() => {
  return Boolean(selectedRoster.value && selectedTemplate.value);
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
}

async function resumeDraft(): Promise<void> {
  if (!resumableDraft.value) {
    return;
  }
  plannerActionError.value = null;
  try {
    await plannerState.resolveDraft(
      resumableDraft.value.draft.roster_id,
      resumableDraft.value.draft.template_id,
    );
    syncSelectionFromWorkspace();
    isPlannerOpen.value = true;
  } catch (error: unknown) {
    plannerState.clearWorkspace();
    plannerActionError.value =
      error instanceof Error ? error.message : "Kunde inte fortsätta utkastet just nu.";
    console.error("Failed to resume classroom planner draft", error);
  }
}

onMounted(async () => {
  try {
    await Promise.all([
      apiGet<PlannerBootstrapResponse>("/api/v1/apps/classroom.group-seating-studio/bootstrap"),
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

async function startPlanning(): Promise<void> {
  if (!selectedRoster.value || !selectedTemplate.value) {
    return;
  }

  plannerActionError.value = null;
  try {
    await plannerState.resolveDraft(selectedRoster.value.id, selectedTemplate.value.id);
    resumableDraft.value = await plannerState.getResumableDraft();
    isPlannerOpen.value = true;
  } catch (error: unknown) {
    plannerActionError.value =
      error instanceof Error ? error.message : "Kunde inte öppna planeringen just nu.";
  }
}

async function resetToSelection(): Promise<void> {
  plannerActionError.value = null;
  try {
    await plannerState.abandonDraft();
    resumableDraft.value = await plannerState.getResumableDraft();
    isPlannerOpen.value = false;
  } catch (error: unknown) {
    plannerActionError.value =
      error instanceof Error ? error.message : "Kunde inte lämna planeringen just nu.";
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
    plannerActionError.value =
      error instanceof Error ? error.message : "Kunde inte avsluta utkastet just nu.";
  }
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
          Välj klass och klassrum, öppna planeringen direkt, och jobba vidare med grupper eller sittplatser utan att behöva ta ställning till alla avancerade funktioner först.
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
      v-if="!isBootstrapping && !bootstrapError && !isPlannerOpen"
      :available-rosters="availableRosters"
      :available-templates="availableTemplates"
      :selected-roster-id="selectedRosterId"
      :selected-template-id="selectedTemplateId"
      :resumable-draft="resumableDraft"
      :is-loading-catalog="isLoadingCatalog"
      :can-start-planning="canStartPlanning"
      @select-roster="selectedRosterId = $event"
      @select-template="selectedTemplateId = $event"
      @create-roster="openRosterCreate"
      @edit-roster="openRosterEdit"
      @create-template="openTemplateCreate"
      @edit-template="openTemplateEdit"
      @start-planning="startPlanning"
      @resume-draft="resumeDraft"
      @discard-resumable-draft="discardResumableDraft"
    />

    <PlannerWorkspaceShell
      v-if="!isBootstrapping && !bootstrapError && isPlannerOpen"
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
