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
  <div class="flex flex-wrap items-center gap-x-4 gap-y-2 border border-navy bg-white px-3 py-2 shadow-brutal-sm">
    <div class="flex-none">
      <slot name="leading" />
    </div>
    <div class="ml-auto flex flex-wrap items-center gap-2 [&_.btn-ghost]:px-3 [&_.btn-ghost]:py-1.5 [&_.btn-primary]:px-3 [&_.btn-primary]:py-1.5 [&_.btn-primary]:shadow-none">
      <slot />
    </div>
  </div>
</template>
