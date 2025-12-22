<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";

type UiJsonOutput = components["schemas"]["UiJsonOutput"];

const props = defineProps<{ output: UiJsonOutput }>();

const pretty = computed(() => {
  try {
    return JSON.stringify(props.output.value, null, 2);
  } catch {
    return String(props.output.value);
  }
});
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm">
    <div
      v-if="output.title"
      class="px-4 py-3 border-b border-navy font-semibold text-navy"
    >
      {{ output.title }}
    </div>
    <pre class="p-4 whitespace-pre-wrap font-mono text-sm text-navy">{{ pretty }}</pre>
  </div>
</template>

