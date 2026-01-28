<script setup lang="ts">
import { ArrowRight } from "lucide-vue-next";

defineProps<{
  size?: number;
  direction?: "right" | "left" | "up" | "down";
}>();
</script>

<template>
  <ArrowRight
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
    :class="{
      'rotate-180': direction === 'left',
      'rotate-90': direction === 'down',
      '-rotate-90': direction === 'up',
    }"
  />
</template>
