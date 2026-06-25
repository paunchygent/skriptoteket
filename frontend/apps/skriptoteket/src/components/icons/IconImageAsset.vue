<script setup lang="ts">
/**
 * Canonical image-asset symbol.
 *
 * Domain purpose:
 *   Represent image files attached to a project-oriented conversion workflow.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - consumed by the Document Converter project rail
 */

import { Image } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Image
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
