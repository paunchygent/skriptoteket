<script setup lang="ts">
/**
 * Canonical grouping workspace symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - uses the approved Tabler fallback where Lucide lacks the clearer group mark
 */

import { IconUsersGroup } from "@tabler/icons-vue";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <IconUsersGroup
    :size="size ?? 24"
    stroke-width="2"
    aria-hidden="true"
  />
</template>
