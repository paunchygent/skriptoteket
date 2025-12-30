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
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <circle
      cx="12"
      cy="12"
      r="9"
    />
    <path d="M9 9a3 3 0 0 1 6 1c0 2-3 3-3 3v1" />
    <circle
      cx="12"
      cy="17"
      r="1"
      fill="currentColor"
      stroke="none"
    />
  </svg>
</template>
