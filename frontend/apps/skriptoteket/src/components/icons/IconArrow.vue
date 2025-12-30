<script setup lang="ts">
defineProps<{
  size?: number;
  direction?: "right" | "left" | "up" | "down";
}>();
</script>

<template>
  <svg
    :width="size ?? 24"
    :height="size ?? 24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="square"
    stroke-linejoin="miter"
    aria-hidden="true"
    :class="{
      'rotate-180': direction === 'left',
      'rotate-90': direction === 'down',
      '-rotate-90': direction === 'up',
    }"
  >
    <!-- Double arrow inspired by HuleEdu design -->
    <path d="M4 12H18" />
    <path d="M12 5L19 12L12 19" />
    <path d="M8 8L12 12L8 16" />
  </svg>
</template>
