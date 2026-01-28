<script setup lang="ts">
import { Download } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Download
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
