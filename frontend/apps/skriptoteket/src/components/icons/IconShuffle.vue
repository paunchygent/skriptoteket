<script setup lang="ts">
import { Shuffle } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Shuffle
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
