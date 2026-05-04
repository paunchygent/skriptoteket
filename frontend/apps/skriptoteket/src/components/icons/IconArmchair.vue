<script setup lang="ts">
/**
 * Armchair icon wrapper.
 *
 * This module exposes the canonical seating-place affordance through the
 * shared icon registry for planner mode switches and seating surfaces.
 */

import { Armchair } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Armchair
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
