<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";

type UiNoticeOutput = components["schemas"]["UiNoticeOutput"];

const props = withDefaults(defineProps<{ output: UiNoticeOutput; density?: "default" | "compact" }>(), {
  density: "default",
});

const variantClasses = computed(() => {
  if (props.output.level === "error") {
    return "border-error text-error";
  }
  if (props.output.level === "warning") {
    return "border-warning text-warning";
  }
  return "border-navy text-navy";
});

const isCompact = computed(() => props.density === "compact");
</script>

<template>
  <div
    :class="[
      isCompact ? 'p-3 border bg-white shadow-brutal-sm' : 'p-4 border bg-white shadow-brutal-sm',
      variantClasses,
    ]"
  >
    <p :class="[isCompact ? 'text-[11px]' : 'text-sm']">
      {{ output.message }}
    </p>
  </div>
</template>
