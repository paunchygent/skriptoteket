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
    aria-hidden="true"
    :class="{
      'rotate-180': direction === 'left',
      'rotate-90': direction === 'down',
      '-rotate-90': direction === 'up',
    }"
  >
    <g
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M2 12H18" />
      <path d="M11 5L18 12L11 19" />
    </g>
  </svg>
</template>
