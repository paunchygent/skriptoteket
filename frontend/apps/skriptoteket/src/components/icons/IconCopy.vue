<script setup lang="ts">
/**
 * Canonical copy-to-clipboard symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by share-link rows and future copy actions
 */

import { Copy } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Copy
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
