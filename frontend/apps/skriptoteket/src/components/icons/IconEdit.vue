<script setup lang="ts">
import { PencilLine } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <PencilLine
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
