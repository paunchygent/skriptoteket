<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";

type UiNoticeOutput = components["schemas"]["UiNoticeOutput"];

const props = defineProps<{ output: UiNoticeOutput }>();

const variantClasses = computed(() => {
  if (props.output.level === "error") {
    return "border-error text-error";
  }
  if (props.output.level === "warning") {
    return "border-warning text-warning";
  }
  return "border-navy text-navy";
});
</script>

<template>
  <div
    class="p-4 border bg-white shadow-brutal-sm"
    :class="variantClasses"
  >
    <p class="text-sm">
      {{ output.message }}
    </p>
  </div>
</template>
