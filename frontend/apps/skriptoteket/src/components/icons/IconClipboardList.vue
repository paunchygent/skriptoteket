<script setup lang="ts">
/**
 * Clipboard-list icon wrapper.
 *
 * This module exposes the canonical overview/list affordance through the
 * shared icon registry for planner navigation.
 */

import { ClipboardList } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ClipboardList
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
