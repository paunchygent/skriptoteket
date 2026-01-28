<script setup lang="ts">
import { Check } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Check
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
