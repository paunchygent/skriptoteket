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
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- Triangle with rounded corners -->
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    <!-- Exclamation line -->
    <path
      d="M12 9V13"
      stroke-width="2"
    />
    <!-- Exclamation dot -->
    <circle
      cx="12"
      cy="17"
      r="1"
      fill="currentColor"
      stroke="none"
    />
  </svg>
</template>
