<script setup lang="ts">
/**
 * Canonical role/permission symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for role and access-control surfaces
 */

import { ShieldUser } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ShieldUser
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
