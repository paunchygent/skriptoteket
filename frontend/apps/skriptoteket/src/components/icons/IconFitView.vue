<script setup lang="ts">
/**
 * Canonical fit-view symbol for canvas scaling controls.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by room/canvas viewport controls and shared dense menus
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
    <path d="M8 5H5v3" />
    <path d="M16 5h3v3" />
    <path d="M19 16v3h-3" />
    <path d="M5 16v3h3" />
    <rect
      x="8.5"
      y="8.5"
      width="7"
      height="7"
      rx="1"
    />
  </svg>
</template>
