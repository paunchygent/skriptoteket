<script setup lang="ts">
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
    stroke-linecap="square"
    stroke-linejoin="miter"
    aria-hidden="true"
  >
    <path d="M6 6L18 18" />
    <path d="M18 6L6 18" />
  </svg>
</template>
