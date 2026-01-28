<script setup lang="ts">
import { Settings } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Settings
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
