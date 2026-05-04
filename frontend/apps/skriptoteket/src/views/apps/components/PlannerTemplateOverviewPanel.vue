<script setup lang="ts">
/**
 * Overview classroom-management panel.
 *
 * This component renders the classroom-side overview controls and compact room
 * preview. It keeps room-preview rendering local to the panel while the
 * parent overview shell owns selection state and modal orchestration.
 */

import { computed, type CSSProperties } from "vue";

import { IconEdit, IconPlus, IconTrash } from "../../../components/icons";
import type { RoomTemplate } from "../classroomPlannerTypes";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import RoomSceneSurface from "./RoomSceneSurface.vue";

const OVERVIEW_PREVIEW_TARGET_WIDTH_PX = 440;
const OVERVIEW_PREVIEW_TARGET_HEIGHT_PX = 224;

const props = defineProps<{
  selectedTemplate: RoomTemplate | null;
  selectedTemplateId: string | null;
  availableTemplates: RoomTemplate[];
  description?: string | null;
  isLoadingWorkspace: boolean;
  showActions?: boolean;
  createDisabledReason?: string | null;
  editDisabledReason?: string | null;
  deleteDisabledReason?: string | null;
}>();

const emit = defineEmits<{
  (e: "select-template", templateId: string | null): void;
  (e: "create-template"): void;
  (e: "edit-current-template", template?: RoomTemplate): void;
  (e: "delete-current-template"): void;
}>();

function selectTemplate(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  emit("select-template", target.value.length > 0 ? target.value : null);
}

const previewGrid = computed(() => {
  return props.selectedTemplate ? normalizeRoomGrid(props.selectedTemplate) : null;
});

const previewMetrics = computed(() => {
  return previewGrid.value ? getRoomSurfaceMetrics(previewGrid.value) : null;
});

const previewScale = computed(() => {
  if (!previewMetrics.value) {
    return 1;
  }
  return Math.min(
    1,
    OVERVIEW_PREVIEW_TARGET_WIDTH_PX / previewMetrics.value.width,
    OVERVIEW_PREVIEW_TARGET_HEIGHT_PX / previewMetrics.value.height,
  );
});

const previewStageStyle = computed<CSSProperties>(() => {
  if (!previewMetrics.value) {
    return {};
  }
  return {
    width: `${previewMetrics.value.width * previewScale.value}px`,
    height: `${previewMetrics.value.height * previewScale.value}px`,
  };
});

const previewSurfaceStyle = computed<CSSProperties>(() => {
  if (!previewMetrics.value) {
    return {};
  }
  return {
    width: `${previewMetrics.value.width}px`,
    height: `${previewMetrics.value.height}px`,
    transform: `scale(${previewScale.value})`,
    transformOrigin: "top left",
  };
});
</script>

<template>
  <article
    class="planner-overview-panel"
    data-test="overview-template-panel"
  >
    <div class="planner-overview-panel-header">
      <div class="flex flex-wrap items-baseline gap-2">
        <p class="text-xl font-semibold text-navy">
          {{ selectedTemplate?.name ?? "Inget klassrum valt" }}
        </p>
        <span
          v-if="selectedTemplate"
          class="text-[0.8rem] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55"
        >
          {{ selectedTemplate.seats.length }} platser
        </span>
      </div>
      <p
        v-if="description"
        class="text-sm text-navy/70"
      >
        {{ description }}
      </p>
    </div>

    <label class="planner-overview-panel-selector">
      <span class="font-semibold">Välj klassrum</span>
      <select
        class="planner-overview-panel-select"
        :disabled="isLoadingWorkspace"
        :value="selectedTemplateId ?? ''"
        data-test="overview-template-select"
        @change="selectTemplate"
      >
        <option value="">
          Utan klassrum
        </option>
        <option
          v-for="template in availableTemplates"
          :key="template.id"
          :value="template.id"
        >
          {{ template.name }}
        </option>
      </select>
    </label>

    <div
      class="planner-overview-panel-preview"
      data-test="overview-classroom-preview"
    >
      <div
        v-if="selectedTemplate && previewGrid"
        class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
        :style="previewStageStyle"
      >
        <div :style="previewSurfaceStyle">
          <RoomSceneSurface
            :grid="previewGrid"
            :seats="selectedTemplate.seats"
            :fixtures="selectedTemplate.fixtures"
            show-backdrop-grid
          />
        </div>
      </div>
      <div
        v-else-if="selectedTemplate"
        class="absolute inset-2 border border-dashed border-navy/10"
      />
      <div
        v-else
        class="planner-overview-panel-empty"
        data-test="overview-classroom-empty"
      >
        Välj ett klassrum i listan ovan för att visa en kompakt förhandsgranskning här.
      </div>
    </div>

    <div
      v-if="showActions !== false"
      class="planner-overview-panel-footer"
    >
      <button
        type="button"
        class="btn-primary planner-overview-panel-action"
        :disabled="Boolean(createDisabledReason)"
        :title="createDisabledReason ?? undefined"
        @click="emit('create-template')"
      >
        <IconPlus :size="14" />
        Nytt klassrum
      </button>
      <button
        type="button"
        class="btn-ghost planner-btn-ghost planner-overview-panel-action"
        :disabled="!selectedTemplate || Boolean(editDisabledReason)"
        :title="editDisabledReason ?? undefined"
        data-test="overview-edit-template"
        @click="emit('edit-current-template', selectedTemplate ?? undefined)"
      >
        <IconEdit :size="14" />
        Redigera
      </button>
      <button
        type="button"
        class="btn-ghost planner-btn-ghost planner-btn-ghost-muted planner-overview-panel-action"
        :disabled="!selectedTemplate || Boolean(deleteDisabledReason)"
        :title="deleteDisabledReason ?? undefined"
        data-test="overview-delete-template"
        @click="emit('delete-current-template')"
      >
        <IconTrash :size="14" />
        Radera
      </button>
    </div>
  </article>
</template>
