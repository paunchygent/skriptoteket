<script setup lang="ts">
/**
 * Canonical create/add symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by dense-tool primitives and future shared create actions
 */

import { Plus } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Plus
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
