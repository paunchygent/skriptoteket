<script setup lang="ts">
/**
 * Shared zoned layout wrapper for planner action rows.
 *
 * Relationships:
 * - semantic shell for grouping, seating, and future planner workspaces
 * - owns the stable `primary`, `context`, and `secondary` zone wrappers
 * - keeps toolbar-specific control composition inside the consuming toolbars
 */

defineSlots<{
  primary?: () => unknown;
  context?: () => unknown;
  secondary?: () => unknown;
}>();

import { ref } from "vue";

const rootRef = ref<HTMLDivElement | null>(null);

defineExpose({
  getRootElement(): HTMLDivElement | null {
    return rootRef.value;
  },
});
</script>

<template>
  <div
    ref="rootRef"
    class="planner-workspace-action-bar flex items-center gap-3 border border-navy bg-panel px-3 py-2 shadow-brutal-sm"
    data-ui="planner-workspace-action-bar"
  >
    <div
      v-if="$slots.primary"
      class="flex shrink-0 items-center gap-1.5"
      data-zone="primary"
    >
      <slot name="primary" />
    </div>
    <div
      v-if="$slots.context"
      class="flex shrink-0 items-center gap-1.5"
      data-zone="context"
    >
      <slot name="context" />
    </div>
    <div
      v-if="$slots.secondary"
      class="ml-auto flex shrink-0 items-center gap-1.5"
      data-zone="secondary"
    >
      <slot name="secondary" />
    </div>
  </div>
</template>
