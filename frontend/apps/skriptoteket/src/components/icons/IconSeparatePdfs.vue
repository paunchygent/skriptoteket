<script setup lang="ts">
/**
 * Canonical separate-PDF output symbol.
 *
 * Domain purpose:
 *   Represent creating distinct PDF files from project source documents.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - consumed by the Document Converter output selector
 */

import { Files } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Files
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
