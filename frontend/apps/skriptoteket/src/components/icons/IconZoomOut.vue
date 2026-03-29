<script setup lang="ts">
/**
 * Canonical zoom-out symbol for dense canvas controls.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by planner/editor viewport and canvas primitives
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
    <circle
      cx="10.5"
      cy="10.5"
      r="5.5"
    />
    <path d="M8 10.5h5" />
    <path d="M15.5 15.5 19 19" />
  </svg>
</template>
