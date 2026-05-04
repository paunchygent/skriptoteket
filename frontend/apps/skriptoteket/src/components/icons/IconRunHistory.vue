<script setup lang="ts">
/**
 * Canonical run-history symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - separates execution history from generic undo/redo controls
 */

import { History } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <History
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
