<script setup lang="ts">
type Props = {
  title: string;
};

defineProps<Props>();
</script>

<template>
  <div class="flex items-center justify-between gap-4">
    <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
      {{ title }}
    </h2>
    <div v-if="$slots.action">
      <slot name="action" />
    </div>
  </div>
</template>
