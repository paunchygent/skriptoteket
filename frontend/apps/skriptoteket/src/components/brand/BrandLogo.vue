<script setup lang="ts">
defineProps<{
  /** Height in pixels or CSS unit. Width scales proportionally (~1:1 aspect ratio). */
  height?: string;
}>();
</script>

<template>
  <img
    src="/logo-horizontal.svg"
    alt="Skriptoteket"
    class="brand-logo"
    :style="height ? { height } : undefined"
  >
</template>

<style scoped>
.brand-logo {
  display: block;
  height: 32px;
  width: auto;
}
</style>
