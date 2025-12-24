<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ output: unknown }>();

const details = computed(() => {
  try {
    return JSON.stringify(props.output, null, 2);
  } catch {
    return String(props.output);
  }
});
</script>

<template>
  <div class="p-4 border border-warning bg-white shadow-brutal-sm">
    <p class="text-sm font-semibold text-warning">
      Okänt output-format
    </p>
    <pre class="mt-2 whitespace-pre-wrap font-mono text-xs text-navy/80">{{ details }}</pre>
  </div>
</template>
