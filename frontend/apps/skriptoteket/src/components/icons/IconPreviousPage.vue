<script setup lang="ts">
/**
 * Canonical previous-page symbol.
 *
 * Domain purpose:
 *   Represent moving backward in a document preview.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - paired with first/next/last page preview controls
 */

import { ChevronLeft } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ChevronLeft
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
