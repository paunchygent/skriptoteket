<script setup lang="ts">
/**
 * Canonical create/add symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by dense-tool primitives and future shared create actions
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
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </svg>
</template>
