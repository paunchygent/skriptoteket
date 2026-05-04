<script setup lang="ts">
/**
 * Canonical individual seat/place symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - keeps chair/place semantics separate from the seating-plan workspace
 */

import { Armchair } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Armchair
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
