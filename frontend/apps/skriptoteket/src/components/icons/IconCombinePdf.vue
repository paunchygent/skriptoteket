<script setup lang="ts">
/**
 * Canonical combined-PDF output symbol.
 *
 * Domain purpose:
 *   Represent collecting multiple source documents into one PDF result.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - consumed by the Document Converter output selector
 */

import { Combine } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Combine
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
