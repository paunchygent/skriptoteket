<script setup lang="ts">
/**
 * Canonical run/execute symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for script/tool execution affordances
 */

import { Play } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Play
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
