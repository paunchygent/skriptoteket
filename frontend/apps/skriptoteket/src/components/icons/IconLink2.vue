<script setup lang="ts">
/**
 * Link icon wrapper.
 *
 * This module exposes the canonical relationship-rule affordance through the
 * shared icon registry so planner tools reuse one icon source.
 */

import { Link2 } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Link2
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
