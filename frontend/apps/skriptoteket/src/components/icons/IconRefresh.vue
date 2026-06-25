<script setup lang="ts">
/**
 * Canonical refresh symbol.
 *
 * Domain purpose:
 *   Represent repeating the current visible operation after inputs changed.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - consumed by preview and retry controls
 */

import { RefreshCw } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <RefreshCw
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
