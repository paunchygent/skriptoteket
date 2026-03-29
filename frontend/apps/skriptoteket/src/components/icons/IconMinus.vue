<script setup lang="ts">
/**
 * Canonical remove/decrement symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - pairs with `IconPlus` for dense stepper-style adjustment controls
 */

defineProps<{
  size?: number;
}>();
</script>

<template>
  <svg
    :width="size ?? 24"
    :height="size ?? 24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2.5"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M5 12h14" />
  </svg>
</template>
