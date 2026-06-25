<script setup lang="ts">
/**
 * Canonical next-page symbol.
 *
 * Domain purpose:
 *   Represent moving forward in a document preview.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - paired with first/previous/last page preview controls
 */

import { ChevronRight } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ChevronRight
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
