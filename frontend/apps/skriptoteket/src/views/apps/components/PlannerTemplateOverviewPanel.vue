<script setup lang="ts">
/**
 * Overview classroom-management panel.
 *
 * This component renders the classroom-side overview controls and compact room
 * preview. It keeps room-preview rendering local to the panel while the
 * parent overview shell owns selection state and modal orchestration.
 */

import { computed, type CSSProperties } from "vue";

import { IconSettings } from "../../../components/icons";
import type { RoomTemplate } from "../classroomPlannerTypes";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import RoomSceneSurface from "./RoomSceneSurface.vue";

const OVERVIEW_PREVIEW_HEIGHT_CLASS = "h-[20rem]";
const OVERVIEW_HEADER_HEIGHT_CLASS = "h-[6rem]";
const OVERVIEW_SELECTOR_HEIGHT_CLASS = "h-[4rem]";
const OVERVIEW_PREVIEW_TARGET_WIDTH_PX = 520;
const OVERVIEW_PREVIEW_TARGET_HEIGHT_PX = 288;

const props = defineProps<{
  selectedTemplate: RoomTemplate | null;
  selectedTemplateId: string | null;
  availableTemplates: RoomTemplate[];
  description: string;
  isLoadingWorkspace: boolean;
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
  <article class="grid grid-rows-[6rem_4rem_20rem_auto] gap-3 border border-navy/20 bg-canvas p-4">
    <div :class="['grid h-full content-start grid-rows-[auto_auto_1fr] gap-2', OVERVIEW_HEADER_HEIGHT_CLASS]">
      <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        Klassrum
      </p>
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
      <p class="text-sm text-navy/70">
        {{ description }}
      </p>
    </div>

    <label :class="['grid h-full content-start gap-2 text-sm text-navy', OVERVIEW_SELECTOR_HEIGHT_CLASS]">
      <span class="font-semibold">Välj klassrum</span>
      <select
        class="w-full border border-navy/25 bg-white px-3 py-2 text-sm text-navy"
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
      v-if="selectedTemplate"
      class="space-y-3"
    >
      <div
        :class="['relative overflow-hidden border border-navy/20 bg-white', OVERVIEW_PREVIEW_HEIGHT_CLASS]"
        data-test="overview-classroom-preview"
      >
        <div
          v-if="previewGrid"
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
          v-else
          class="absolute inset-2 border border-dashed border-navy/10"
        />
      </div>
    </div>

    <div
      v-else
      :class="['flex items-center justify-center border border-dashed border-navy/25 bg-white px-4 py-8 text-center text-sm text-navy/55', OVERVIEW_PREVIEW_HEIGHT_CLASS]"
      data-test="overview-classroom-empty"
    >
      Välj ett klassrum i listan ovan för att visa en kompakt förhandsgranskning här.
    </div>

    <div class="grid gap-2 border-t border-navy/15 pt-2.5 md:grid-cols-3">
      <button
        type="button"
        class="btn-primary w-full justify-center"
        @click="emit('create-template')"
      >
        Nytt klassrum
      </button>
      <button
        type="button"
        class="btn-ghost inline-flex w-full items-center justify-center gap-2 border-navy/30 bg-white shadow-none"
        :disabled="!selectedTemplate"
        @click="emit('edit-current-template', selectedTemplate ?? undefined)"
      >
        <IconSettings :size="14" />
        Redigera klassrum
      </button>
      <button
        type="button"
        class="btn-ghost w-full justify-center border-navy/30 bg-white text-navy/50 shadow-none hover:text-burgundy disabled:text-navy/40"
        :disabled="!selectedTemplate"
        data-test="overview-delete-template"
        @click="emit('delete-current-template')"
      >
        Ta bort klassrum
      </button>
    </div>
  </article>
</template>
