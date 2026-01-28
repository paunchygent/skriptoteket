<script setup lang="ts">
import { Search } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Search
    :size="size ?? 18"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
