<script setup lang="ts">
/**
 * Canonical rules workspace symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - avoids using settings/gear semantics for classroom rules
 */

import { ListChecks } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ListChecks
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
