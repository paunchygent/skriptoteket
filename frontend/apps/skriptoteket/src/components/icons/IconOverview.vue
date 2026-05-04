<script setup lang="ts">
/**
 * Canonical overview workspace symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - keeps planner overview distinct from class-list/clipboard semantics
 */

import { LayoutDashboard } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <LayoutDashboard
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
