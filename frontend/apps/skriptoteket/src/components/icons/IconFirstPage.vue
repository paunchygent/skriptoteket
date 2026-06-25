<script setup lang="ts">
/**
 * Canonical first-page symbol.
 *
 * Domain purpose:
 *   Represent moving to the first page in a document preview.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - paired with previous/next/last page preview controls
 */

import { ChevronsLeft } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ChevronsLeft
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
