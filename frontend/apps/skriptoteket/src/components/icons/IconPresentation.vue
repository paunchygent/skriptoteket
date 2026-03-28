<script setup lang="ts">
/**
 * Presentation icon wrapper.
 *
 * This module exposes the canonical planning-map affordance through the shared
 * icon registry for the dedicated rules workspace.
 */

import { Presentation } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Presentation
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
