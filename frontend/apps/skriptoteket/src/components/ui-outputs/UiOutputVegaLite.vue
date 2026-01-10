<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";

type UiVegaLiteOutput = components["schemas"]["UiVegaLiteOutput"];

const props = withDefaults(defineProps<{ output: UiVegaLiteOutput; density?: "default" | "compact" }>(), {
  density: "default",
});

const isCompact = computed(() => props.density === "compact");
</script>

<template>
  <div
    :class="[
      isCompact ? 'p-3 border-2 bg-white shadow-none' : 'p-4 border bg-white shadow-brutal-sm',
      'border-warning text-warning',
    ]"
  >
    <p :class="[isCompact ? 'text-[11px]' : 'text-sm']">
      Vega-Lite stöds inte ännu i klienten.
    </p>
  </div>
</template>
