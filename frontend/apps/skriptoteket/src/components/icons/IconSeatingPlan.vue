<script setup lang="ts">
/**
 * Canonical seating-plan workspace symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - distinguishes the seating workspace from an individual chair/place
 */

import { LayoutGrid } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <LayoutGrid
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
