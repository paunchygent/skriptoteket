<script setup lang="ts">
defineProps<{
  size?: number;
  filled?: boolean;
}>();
</script>

<template>
  <svg
    :width="size ?? 24"
    :height="size ?? 24"
    viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'"
    stroke="currentColor"
    stroke-width="2"
    stroke-linejoin="miter"
    aria-hidden="true"
  >
    <path d="M7 4h10v16l-5-3-5 3z" />
  </svg>
</template>
