<script setup lang="ts">
/**
 * Planner workspace shell.
 *
 * This component renders the active classroom-planning workspace after a draft
 * has been created or resumed. It keeps the default surface focused on one
 * teacher task at a time so grouping and seating do not teach a shared
 * whole-workspace mental model.
 */

import { computed, ref, watch } from "vue";

import type { RoomTemplate } from "../classroomPlannerTypes";
import GroupBoard from "./GroupBoard.vue";
import PlannerMetadataDrawer from "./PlannerMetadataDrawer.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";
import RoomCanvas from "./RoomCanvas.vue";
import { useClassroomState } from "../useClassroomState";

type PlannerView = "groups" | "seats";

const props = withDefaults(
  defineProps<{
    availableTemplates?: RoomTemplate[];
    initialView?: PlannerView;
  }>(),
  {
    availableTemplates: () => [],
    initialView: "groups",
  },
);

const emit = defineEmits<{
  (e: "change-grouping-template", payload: { templateId: string | null }): void;
  (e: "change-seating-template", payload: { templateId: string | null }): void;
  (e: "select-workspace-mode", mode: "overview" | "grouping" | "seating"): void;
  (e: "exit-to-landing"): void;
}>();

const plannerState = useClassroomState();

function resolvePlannerView(requestedView: PlannerView): PlannerView {
  if (plannerState.draft?.draft_kind === "grouping") {
    return "groups";
  }
  if (plannerState.draft?.draft_kind === "seating") {
    return "seats";
  }
  return requestedView;
}

const currentView = ref<PlannerView>(resolvePlannerView(props.initialView));
const selectedStudentId = ref<string | null>(null);
const isMetadataDrawerOpen = ref(false);
const pendingGroupingTemplateId = ref("");
const pendingSeatingTemplateId = ref("");
const plannerTitle = computed(() => plannerState.roster?.name ?? "Klassarbetsyta");
const currentWorkspaceLabel = computed(() => {
  return currentView.value === "groups" ? "Grupper" : "Sittplatser";
});
const workspaceModeValue = computed<"overview" | "grouping" | "seating">(() => {
  return currentView.value === "groups" ? "grouping" : "seating";
});
const isSeatWorkspaceWithoutTemplate = computed(() => {
  return currentView.value === "seats" && plannerState.template === null;
});
const workspaceContextLabel = computed(() => plannerState.template?.name ?? "Utan klassrum");
const saveStatusLabel = computed(() => {
  switch (plannerState.saveStatus) {
    case "saving":
      return "Sparar";
    case "saved":
      return "Sparad";
    case "error":
      return "Inte sparad";
    case "conflict":
      return "Konflikt";
    default:
      return "Ingen ändring";
  }
});
const saveStatusTone = computed<"neutral" | "success" | "warning" | "danger">(() => {
  switch (plannerState.saveStatus) {
    case "saved":
      return "success";
    case "saving":
      return "warning";
    case "error":
    case "conflict":
      return "danger";
    default:
      return "neutral";
  }
});
const hasSaveMessage = computed(() => {
  return typeof plannerState.saveMessage === "string" && plannerState.saveMessage.length > 0;
});

const currentViewHint = computed(() => {
  if (isSeatWorkspaceWithoutTemplate.value) {
    return "Välj eller byt klassrum direkt här i sittarbetsytan.";
  }
  if (currentView.value === "groups") {
    return "Dra elever mellan grupperna tills grupparbetet sitter.";
  }
  return "Dra elever till platserna och öppna elevanteckningar vid behov.";
});

function selectStudent(studentId: string): void {
  selectedStudentId.value = studentId;
  if (currentView.value !== "seats") {
    isMetadataDrawerOpen.value = false;
    return;
  }
  isMetadataDrawerOpen.value = true;
}

async function reloadAfterConflict(): Promise<void> {
  await plannerState.reloadActiveWorkspace();
}

function changeSeatingTemplateFromEvent(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }

  pendingSeatingTemplateId.value = target.value;
  emit("change-seating-template", { templateId: pendingSeatingTemplateId.value || null });
}

function changeGroupingTemplateFromEvent(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }

  pendingGroupingTemplateId.value = target.value;
  emit("change-grouping-template", { templateId: pendingGroupingTemplateId.value || null });
}

function selectWorkspaceMode(value: string): void {
  if (value === "overview" || value === "grouping" || value === "seating") {
    emit("select-workspace-mode", value);
  }
}

watch(
  () => props.initialView,
  (nextView) => {
    currentView.value = resolvePlannerView(nextView);
    isMetadataDrawerOpen.value = false;
    selectedStudentId.value = null;
  },
);

watch(
  () => [plannerState.draft?.draft_kind ?? null, plannerState.template?.id ?? null] as const,
  () => {
    currentView.value = resolvePlannerView(currentView.value);
    isMetadataDrawerOpen.value = false;
    selectedStudentId.value = null;
    pendingGroupingTemplateId.value = plannerState.template?.id ?? "";
    pendingSeatingTemplateId.value = plannerState.template?.id ?? "";
  },
);

</script>

<template>
  <section class="space-y-6">
    <div
      v-if="plannerState.saveStatus === 'conflict'"
      class="system-message system-message-warning"
    >
      <div class="system-message-content">
        {{ plannerState.saveMessage }}
      </div>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none"
        @click="reloadAfterConflict"
      >
        Ladda om utkast
      </button>
    </div>

    <PlannerTopPanel
      :title="plannerTitle"
      :context-label="`${currentWorkspaceLabel} · ${isSeatWorkspaceWithoutTemplate ? 'välj klassrum i arbetsytan' : `${workspaceContextLabel} · version ${plannerState.draft?.revision ?? 0}`}`"
      :mode-value="workspaceModeValue"
      :supporting-text="currentViewHint"
      :status-label="saveStatusLabel"
      :status-message="hasSaveMessage ? plannerState.saveMessage : null"
      :status-tone="saveStatusTone"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-to-landing')"
    />

    <article
      v-if="currentView === 'groups'"
      class="space-y-3 border border-navy/20 bg-white p-4 shadow-brutal-sm"
    >
      <div class="flex flex-col gap-3 border-b border-navy/20 pb-3 lg:flex-row lg:items-end lg:justify-between">
        <div class="space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Klassrumsstöd
          </p>
          <h3 class="font-serif text-xl text-navy md:text-2xl">
            {{ plannerState.template?.name ?? "Grupper utan klassrumsstöd" }}
          </h3>
          <p class="max-w-[42rem] text-sm leading-relaxed text-navy/70">
            Låt grupperna vara fria eller välj ett klassrum när rummets kontext ska hjälpa arbetet.
          </p>
        </div>

        <label class="block min-w-[18rem] space-y-2">
          <span class="block text-sm font-semibold text-navy">Rumsmall</span>
          <select
            class="w-full border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
            :value="plannerState.template?.id ?? pendingGroupingTemplateId"
            @change="changeGroupingTemplateFromEvent"
          >
            <option value="">
              Arbeta utan klassrum
            </option>
            <option
              v-for="template in availableTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} · {{ template.seats.length }} platser
            </option>
          </select>
        </label>
      </div>
    </article>

    <article
      v-if="currentView === 'seats'"
      class="space-y-3 border border-navy/20 bg-white p-4 shadow-brutal-sm"
    >
      <div class="flex flex-col gap-3 border-b border-navy/20 pb-3 lg:flex-row lg:items-end lg:justify-between">
        <div class="space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Klassrum
          </p>
          <h3 class="font-serif text-xl text-navy md:text-2xl">
            {{ plannerState.template?.name ?? "Välj klassrum för sittplatserna" }}
          </h3>
          <p class="max-w-[42rem] text-sm leading-relaxed text-navy/70">
            Byt rum här när samma klass behöver en ny sittplacering i en annan sal.
          </p>
        </div>

        <label class="block min-w-[18rem] space-y-2">
          <span class="block text-sm font-semibold text-navy">Rumsmall</span>
          <select
            class="w-full border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
            :value="plannerState.template?.id ?? pendingSeatingTemplateId"
            @change="changeSeatingTemplateFromEvent"
          >
            <option value="">
              Välj rumsmall
            </option>
            <option
              v-for="template in availableTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} · {{ template.seats.length }} platser
            </option>
          </select>
        </label>
      </div>

      <div
        v-if="isSeatWorkspaceWithoutTemplate"
        class="border border-dashed border-navy/30 bg-canvas px-6 py-8 text-center text-sm leading-relaxed text-navy/70"
      >
        Välj ett klassrum ovan för att öppna whiteboardytan. Du kan byta rum här senare utan att lämna sittarbetsytan.
      </div>
    </article>

    <GroupBoard
      v-if="currentView === 'groups'"
      :selected-student-id="selectedStudentId"
      @student-selected="selectStudent"
    />
    <RoomCanvas
      v-else-if="!isSeatWorkspaceWithoutTemplate"
      :selected-student-id="selectedStudentId"
      @student-selected="selectStudent"
    />

    <PlannerMetadataDrawer
      :selected-student-id="selectedStudentId"
      :open="isMetadataDrawerOpen"
      @close="isMetadataDrawerOpen = false"
    />
  </section>
</template>
