<script setup lang="ts">
import { MoreVertical } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <MoreVertical
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
