<script setup lang="ts">
/**
 * Canonical teacher-anchor rule symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by near-teacher rule tools without implying a school building
 */

import { UserStar } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <UserStar
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
