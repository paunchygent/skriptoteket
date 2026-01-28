<script setup lang="ts">
import { Info } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Info
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
