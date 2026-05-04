<script setup lang="ts">
/**
 * Share/export scope selector for Klassrumskartan.
 *
 * Relationships:
 * - used by `PlannerShareExportPanel` when one share surface can target more
 *   than one planner draft kind
 * - emits semantic scope selections while the parent owns panel state
 */

import { IconCheck } from "../../../components/icons";
import type { PlannerShareExportScopeOption } from "./plannerShareExportActions";

defineProps<{
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
    <div class="grid gap-1.5">
      <button
        v-for="option in scopeOptions"
        :key="option.value"
        type="button"
        class="grid min-h-10 grid-cols-[auto_minmax(0,1fr)] items-center gap-2 rounded-[4px] border px-2.5 text-left text-navy transition-colors disabled:cursor-not-allowed disabled:opacity-50"
        :class="option.value === scopeValue ? 'border-navy/35 bg-canvas' : 'border-navy/20 bg-white hover:border-navy/35 hover:bg-canvas/70'"
        :disabled="option.disabled"
        :title="option.disabledReason ?? undefined"
        :aria-pressed="option.value === scopeValue"
        :data-test="`planner-share-export-scope-${option.value}`"
        @click="selectScope(option)"
      >
        <IconCheck
          v-if="option.value === scopeValue"
          :size="13"
        />
        <span
          v-else
          class="h-[13px] w-[13px]"
          aria-hidden="true"
        />
        <span class="truncate text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)]">
          {{ option.label }}
        </span>
      </button>
    </div>
  </section>
</template>
