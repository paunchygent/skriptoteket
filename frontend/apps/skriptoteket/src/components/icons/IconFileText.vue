<script setup lang="ts">
/**
 * Canonical text/PDF-file symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by export affordances when the file type is a document/PDF
 */

import { FileText } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <FileText
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
