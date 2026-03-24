<script setup lang="ts">
/**
 * Overview roster-management panel.
 *
 * This component renders the class-side overview controls and compact student
 * preview. It stays prop/event-driven so the parent overview shell can own
 * workspace-level state and modal orchestration.
 */

import type { Roster } from "../classroomPlannerTypes";

const OVERVIEW_PREVIEW_HEIGHT_CLASS = "h-[20rem]";
const OVERVIEW_HEADER_HEIGHT_CLASS = "h-[6rem]";
const OVERVIEW_SELECTOR_HEIGHT_CLASS = "h-[4rem]";

const props = defineProps<{
  title: string;
  countLabel: string;
  description: string;
  selectedRoster: Roster | null;
  selectedRosterId: string | null;
  availableRosters: Roster[];
  selectedRosterPreviewNames: string[];
  isLoadingWorkspace: boolean;
}>();

const emit = defineEmits<{
  (e: "select-roster", rosterId: string): void;
  (e: "create-roster"): void;
  (e: "edit-roster"): void;
  (e: "delete-current-roster"): void;
}>();

function selectRoster(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  if (target.value && target.value !== props.selectedRosterId) {
    emit("select-roster", target.value);
  }
}
</script>

<template>
  <article class="grid grid-rows-[6rem_4rem_20rem_auto] gap-3 border border-navy/20 bg-canvas p-4">
    <div :class="['grid h-full content-start grid-rows-[auto_auto_1fr] gap-2', OVERVIEW_HEADER_HEIGHT_CLASS]">
      <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        Klass
      </p>
      <div class="flex flex-wrap items-baseline gap-2">
        <p class="text-xl font-semibold text-navy">
          {{ title }}
        </p>
        <span class="text-[0.8rem] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
          {{ countLabel }}
        </span>
      </div>
      <p class="text-sm text-navy/70">
        {{ description }}
      </p>
    </div>

    <label :class="['grid h-full content-start gap-2 text-sm text-navy', OVERVIEW_SELECTOR_HEIGHT_CLASS]">
      <span class="font-semibold">Byt klass</span>
      <select
        class="w-full border border-navy/25 bg-white px-3 py-2 text-sm text-navy"
        :disabled="isLoadingWorkspace"
        :value="selectedRosterId ?? ''"
        data-test="overview-roster-select"
        @change="selectRoster"
      >
        <option
          v-if="!selectedRosterId"
          value=""
        >
          Välj klasslista
        </option>
        <option
          v-for="roster in availableRosters"
          :key="roster.id"
          :value="roster.id"
        >
          {{ roster.name }}
        </option>
      </select>
    </label>

    <div
      :class="['relative overflow-hidden border border-navy/20 bg-white', OVERVIEW_PREVIEW_HEIGHT_CLASS]"
      data-test="overview-roster-preview"
    >
      <div
        v-if="selectedRoster && selectedRosterPreviewNames.length > 0"
        class="grid h-full grid-cols-3 content-start gap-x-4 gap-y-1 overflow-hidden p-4 text-[0.8rem] leading-5 text-navy/72"
      >
        <span
          v-for="name in selectedRosterPreviewNames"
          :key="name"
          class="truncate"
        >
          {{ name }}
        </span>
      </div>
      <div
        v-else
        class="flex h-full items-center justify-center p-4 text-center text-sm text-navy/55"
      >
        Välj en klasslista för att visa en kompakt elevöversikt här.
      </div>
    </div>

    <div class="grid gap-2 border-t border-navy/15 pt-2.5 md:grid-cols-3">
      <button
        type="button"
        class="btn-primary w-full justify-center"
        @click="emit('create-roster')"
      >
        Ny klasslista
      </button>
      <button
        type="button"
        class="btn-ghost w-full justify-center border-navy/30 bg-white shadow-none"
        :disabled="!selectedRoster"
        @click="emit('edit-roster')"
      >
        Redigera klass
      </button>
      <button
        type="button"
        class="btn-ghost w-full justify-center border-navy/30 bg-white text-burgundy shadow-none disabled:text-navy/40"
        :disabled="!selectedRoster"
        data-test="overview-delete-roster"
        @click="emit('delete-current-roster')"
      >
        Ta bort klasslista
      </button>
    </div>
  </article>
</template>
