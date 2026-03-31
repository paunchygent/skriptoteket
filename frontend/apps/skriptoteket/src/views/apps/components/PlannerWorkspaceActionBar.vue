<script setup lang="ts">
/**
 * Shared layout wrapper for planner action rows.
 *
 * This component keeps the grouping and seating toolbars visually consistent
 * without forcing their task-specific actions into one schema-driven control.
 */

defineSlots<{
  leading?: () => unknown;
  default?: () => unknown;
}>();
</script>

<template>
  <div
    class="flex items-center gap-3 overflow-visible border border-navy bg-white px-3 py-2 shadow-brutal-sm"
    data-ui="planner-workspace-action-bar"
  >
    <div class="flex shrink-0 items-center gap-1.5">
      <slot name="leading" />
    </div>
    <div class="ml-auto flex shrink-0 items-center gap-1.5">
      <slot />
    </div>
  </div>
</template>
