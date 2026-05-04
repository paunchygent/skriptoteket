<script setup lang="ts">
/**
 * Canonical keep-near relationship-rule symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - keeps `IconLink2` reserved for real link/share semantics
 */

import { Magnet } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Magnet
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
