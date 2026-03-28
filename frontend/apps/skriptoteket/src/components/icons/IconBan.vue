<script setup lang="ts">
/**
 * Ban icon wrapper.
 *
 * This module exposes the canonical banned/clear affordance through the shared
 * icon registry so planner surfaces do not inline ad hoc SVGs.
 */

import { Ban } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Ban
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
