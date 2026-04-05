<script setup lang="ts">
/**
 * Overview roster-management panel.
 *
 * This component renders the class-side overview controls and compact student
 * preview. It stays prop/event-driven so the parent overview shell can own
 * workspace-level state and modal orchestration.
 */

import { IconSettings } from "../../../components/icons";
import type { Roster } from "../classroomPlannerTypes";

const props = defineProps<{
  title: string;
  countLabel: string;
  description?: string | null;
  selectedRoster: Roster | null;
  selectedRosterId: string | null;
  availableRosters: Roster[];
  selectedRosterPreviewNames: string[];
  isLoadingWorkspace: boolean;
  showActions?: boolean;
  createDisabledReason?: string | null;
  editDisabledReason?: string | null;
  deleteDisabledReason?: string | null;
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
  <article
    class="planner-overview-panel"
    data-test="overview-roster-panel"
  >
    <div class="planner-overview-panel-header">
      <div class="flex flex-wrap items-baseline gap-2">
        <p class="text-xl font-semibold text-navy">
          {{ title }}
        </p>
        <span class="text-[0.8rem] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
          {{ countLabel }}
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
      <span class="font-semibold">Byt klass</span>
      <select
        class="planner-overview-panel-select"
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
      class="planner-overview-panel-preview overflow-y-auto"
      data-test="overview-roster-preview"
    >
      <div
        v-if="selectedRoster && selectedRosterPreviewNames.length > 0"
        class="grid grid-cols-3 content-start gap-x-3 gap-y-1 p-3 text-[0.8rem] leading-5 text-navy/72"
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
        class="planner-overview-panel-empty"
      >
        Välj en klasslista för att visa en kompakt elevöversikt här.
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
        @click="emit('create-roster')"
      >
        Ny klasslista
      </button>
      <button
        type="button"
        class="btn-ghost planner-btn-ghost planner-overview-panel-action"
        :disabled="!selectedRoster || Boolean(editDisabledReason)"
        :title="editDisabledReason ?? undefined"
        data-test="overview-edit-roster"
        @click="emit('edit-roster')"
      >
        <IconSettings :size="14" />
        Redigera
      </button>
      <button
        type="button"
        class="btn-ghost planner-btn-ghost planner-btn-ghost-muted planner-overview-panel-action"
        :disabled="!selectedRoster || Boolean(deleteDisabledReason)"
        :title="deleteDisabledReason ?? undefined"
        data-test="overview-delete-roster"
        @click="emit('delete-current-roster')"
      >
        Ta bort klasslista
      </button>
    </div>
  </article>
</template>
