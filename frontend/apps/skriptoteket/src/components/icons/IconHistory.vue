<script setup lang="ts">
import { History } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <History
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
