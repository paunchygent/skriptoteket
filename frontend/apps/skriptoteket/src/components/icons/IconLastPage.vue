<script setup lang="ts">
/**
 * Canonical last-page symbol.
 *
 * Domain purpose:
 *   Represent moving to the last page in a document preview.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - paired with first/previous/next page preview controls
 */

import { ChevronsRight } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ChevronsRight
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
