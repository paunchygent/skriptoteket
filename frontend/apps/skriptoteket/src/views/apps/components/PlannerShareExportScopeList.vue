<script setup lang="ts">
/**
 * Share/export scope selector for Klassrumskartan.
 *
 * Relationships:
 * - used by `PlannerShareExportPanel` when one share surface can target more
 *   than one planner draft kind
 * - emits semantic scope selections while the parent owns panel state
 */

import { computed } from "vue";

import { IconGroupsWorkspace, IconSeatingPlan } from "../../../components/icons";
import type { PlannerShareExportScopeOption } from "./plannerShareExportActions";

const props = defineProps<{
  scopeValue?: string | null;
  scopeOptions: PlannerShareExportScopeOption[];
}>();

const emit = defineEmits<{
  (e: "select-scope", value: string): void;
}>();

function selectScope(option: PlannerShareExportScopeOption): void {
  if (option.disabled) {
    return;
  }
  emit("select-scope", option.value);
}

const selectedOption = computed(() => {
  return props.scopeOptions.find((option) => option.value === props.scopeValue) ?? null;
});
const selectedSummary = computed(() => selectedOption.value?.summary ?? null);
const prerequisiteNotice = computed(() => {
  const disabledOption = props.scopeOptions.find((option) => option.disabled && option.disabledReason);
  if (!disabledOption?.disabledReason) {
    return null;
  }
  if (!selectedOption.value) {
    return disabledOption.disabledReason;
  }
  return `${disabledOption.label}: ${disabledOption.disabledReason}`;
});

function scopeIcon(option: PlannerShareExportScopeOption) {
  return option.value === "seating" ? IconSeatingPlan : IconGroupsWorkspace;
}
</script>

<template>
  <section
    v-if="scopeOptions.length > 0"
    class="border-b border-navy/15 px-3.5 py-3 md:px-4"
    aria-label="Välj vad som ska delas"
  >
    <p class="mb-2 text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/65">
      Välj innehåll
    </p>
    <div
      class="planner-share-export-scope-rail grid grid-cols-2 gap-1 rounded-[4px] border border-navy/20 bg-panel-muted p-1"
      role="group"
      aria-label="Välj innehållstyp"
    >
      <button
        v-for="option in scopeOptions"
        :key="option.value"
        type="button"
        class="planner-share-export-scope-option grid min-h-9 grid-cols-[auto_minmax(0,1fr)] items-center gap-1.5 rounded-[3px] border px-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50"
        :class="option.value === scopeValue ? 'border-action bg-action text-button-primary-text' : 'border-transparent bg-canvas/50 text-navy hover:border-action/45 hover:bg-action/5'"
        :disabled="option.disabled"
        :title="option.disabledReason ?? undefined"
        :aria-pressed="option.value === scopeValue"
        :data-test="`planner-share-export-scope-${option.value}`"
        @click="selectScope(option)"
      >
        <component
          :is="scopeIcon(option)"
          :size="13"
          aria-hidden="true"
        />
        <span class="min-w-0 text-[10px] font-semibold uppercase leading-tight tracking-normal">
          {{ option.label }}
        </span>
      </button>
    </div>
    <div
      v-if="selectedSummary"
      class="mt-3 rounded-[4px] border border-navy/20 bg-canvas/55 px-3 py-2.5 text-navy"
      data-test="planner-share-export-scope-summary"
    >
      <div class="min-w-0">
        <p class="text-[11px] font-semibold leading-tight text-action">
          Valt innehåll
        </p>
        <p
          class="break-words text-sm font-semibold leading-snug text-navy"
          data-test="planner-share-export-scope-context"
        >
          {{ selectedSummary.contextLabel }}
        </p>
        <p
          class="break-words text-[11px] leading-snug text-navy/65"
          data-test="planner-share-export-scope-meta"
        >
          {{ [selectedSummary.kindLabel, ...(selectedSummary.details ?? [])].filter(Boolean).join(" · ") }}
        </p>
      </div>
    </div>
    <p
      v-if="prerequisiteNotice"
      class="mt-2 text-[11px] leading-snug text-navy/60"
      data-test="planner-share-export-scope-prerequisite"
    >
      {{ prerequisiteNotice }}
    </p>
  </section>
</template>
