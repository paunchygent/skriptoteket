<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";

type UiJsonOutput = components["schemas"]["UiJsonOutput"];

const props = withDefaults(defineProps<{ output: UiJsonOutput; density?: "default" | "compact" }>(), {
  density: "default",
});

const isCompact = computed(() => props.density === "compact");

const pretty = computed(() => {
  try {
    return JSON.stringify(props.output.value, null, 2);
  } catch {
    return String(props.output.value);
  }
});
</script>

<template>
  <div :class="[isCompact ? 'panel-inset' : 'border border-navy bg-white shadow-brutal-sm']">
    <div
      v-if="output.title"
      :class="[isCompact ? 'px-3 py-2 border-b border-navy/20 font-semibold text-[11px] text-navy' : 'px-4 py-3 border-b border-navy font-semibold text-navy']"
    >
      {{ output.title }}
    </div>
    <pre :class="[isCompact ? 'p-3 whitespace-pre-wrap font-mono text-[11px] text-navy' : 'p-4 whitespace-pre-wrap font-mono text-sm text-navy']">{{ pretty }}</pre>
  </div>
</template>
