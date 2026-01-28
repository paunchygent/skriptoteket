<script setup lang="ts">
import { Trash2 } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Trash2
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
