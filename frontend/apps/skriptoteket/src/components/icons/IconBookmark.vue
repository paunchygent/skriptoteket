<script setup lang="ts">
import { Bookmark } from "lucide-vue-next";

defineProps<{
  size?: number;
  filled?: boolean;
}>();
</script>

<template>
  <Bookmark
    :size="size ?? 24"
    :stroke-width="2.5"
    :fill="filled ? 'currentColor' : 'none'"
    aria-hidden="true"
  />
</template>
