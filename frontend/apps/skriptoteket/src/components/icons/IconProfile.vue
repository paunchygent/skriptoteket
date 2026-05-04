<script setup lang="ts">
/**
 * Canonical user-profile symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for account and identity surfaces
 */

import { CircleUserRound } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <CircleUserRound
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
