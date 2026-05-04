<script setup lang="ts">
/**
 * Canonical students symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by planner student-list and student-pool surfaces
 */

import { UsersRound } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <UsersRound
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
