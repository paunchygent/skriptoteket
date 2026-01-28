<script setup lang="ts">
import { X } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <X
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
