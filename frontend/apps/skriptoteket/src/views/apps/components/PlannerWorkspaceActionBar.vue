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
  <div class="flex flex-wrap items-end justify-end gap-2 border border-navy bg-white p-4 shadow-brutal-sm">
    <slot name="leading" />
    <slot />
  </div>
</template>
