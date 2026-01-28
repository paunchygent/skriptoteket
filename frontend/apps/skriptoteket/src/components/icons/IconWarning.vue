<script setup lang="ts">
import { AlertTriangle } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <AlertTriangle
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
