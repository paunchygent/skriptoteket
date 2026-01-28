<script setup lang="ts">
import { Undo2 } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Undo2
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
