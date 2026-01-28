<script setup lang="ts">
import { CircleHelp } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <CircleHelp
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
