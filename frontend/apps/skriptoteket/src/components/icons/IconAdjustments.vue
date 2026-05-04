<script setup lang="ts">
/**
 * Canonical configure-context symbol.
 *
 * Relationships:
 * - replaces ambiguous gear-as-rules usage in shared dense-tool contracts
 * - exported through `src/components/icons/index.ts`
 */

import { SlidersHorizontal } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <SlidersHorizontal
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
