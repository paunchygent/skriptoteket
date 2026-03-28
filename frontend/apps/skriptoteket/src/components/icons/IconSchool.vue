<script setup lang="ts">
/**
 * School icon wrapper.
 *
 * This module exposes the canonical teacher/near-school affordance through
 * the shared icon registry for smart-rule controls.
 */

import { School } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <School
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
