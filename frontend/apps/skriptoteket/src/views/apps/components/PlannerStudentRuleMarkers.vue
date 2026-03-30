<script setup lang="ts">
/**
 * Shared smart-rule marker chips for planner student rows.
 *
 * This component keeps the visible rule badges consistent across student-pool
 * rows and grouped student bars so teachers can read the same smart-rule
 * signal wherever a student is currently shown.
 */

withDefaults(defineProps<{
  markers?: string[];
  rootTestId?: string;
}>(), {
  markers: () => [],
  rootTestId: undefined,
});
</script>

<template>
  <div
    v-if="markers.length > 0"
    class="flex flex-wrap gap-1"
    :data-test="rootTestId"
  >
    <span
      v-for="marker in markers"
      :key="marker"
      class="border border-navy/20 bg-canvas px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70"
    >
      {{ marker }}
    </span>
  </div>
</template>
