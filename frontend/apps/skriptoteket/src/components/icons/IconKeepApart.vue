<script setup lang="ts">
/**
 * Canonical keep-apart relationship-rule symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by seating-rule tools and active-rule summaries
 */

import { Ban } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Ban
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
