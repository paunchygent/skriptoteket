<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiVegaLiteOutput = components["schemas"]["UiVegaLiteOutput"];

defineProps<{ output: UiVegaLiteOutput }>();
</script>

<template>
  <div class="p-4 border border-error bg-white shadow-brutal-sm">
    <p class="text-sm text-error">
      Vega-Lite stöds inte ännu i klienten.
    </p>
  </div>
</template>

