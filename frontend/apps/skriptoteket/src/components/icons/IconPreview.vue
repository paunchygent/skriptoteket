<script setup lang="ts">
/**
 * Canonical preview symbol.
 *
 * Domain purpose:
 *   Represent opening or refreshing a visible document preview.
 *
 * Relationships:
 *   - exported through `src/components/icons/index.ts`
 *   - consumed by document-oriented curated app controls
 */

import { Eye } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Eye
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
