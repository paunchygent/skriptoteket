<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{ output: unknown; density?: "default" | "compact" }>(), {
  density: "default",
});

const isCompact = computed(() => props.density === "compact");

const details = computed(() => {
  try {
    return JSON.stringify(props.output, null, 2);
  } catch {
    return String(props.output);
  }
});
</script>

<template>
  <div :class="[isCompact ? 'p-3 border border-warning bg-white shadow-brutal-sm' : 'p-4 border border-warning bg-white shadow-brutal-sm']">
    <p :class="[isCompact ? 'text-[11px] font-semibold text-warning' : 'text-sm font-semibold text-warning']">
      Okänt output-format
    </p>
    <pre :class="[isCompact ? 'mt-2 whitespace-pre-wrap font-mono text-[11px] text-navy/80' : 'mt-2 whitespace-pre-wrap font-mono text-xs text-navy/80']">{{ details }}</pre>
  </div>
</template>
