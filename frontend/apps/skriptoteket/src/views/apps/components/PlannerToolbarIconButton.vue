<script setup lang="ts">
/**
 * Compact icon-first toolbar button for planner action rows.
 *
 * Relationships:
 * - thin planner-facing adapter over the shared `UiDenseActionButton` primitive
 * - preserves existing planner call sites while the shared dense-tool layer settles
 */

import { UiDenseActionButton } from "../../../components/ui";
import type { DenseActionGroupPosition, DenseActionSize } from "../../../components/ui";

defineProps<{
  label: string;
  title?: string;
  disabled?: boolean;
  size?: DenseActionSize;
  groupPosition?: DenseActionGroupPosition;
}>();
</script>

<template>
  <UiDenseActionButton
    icon-only
    :label="label"
    :title="title ?? label"
    :disabled="disabled"
    :size="size"
    :group-position="groupPosition"
  >
    <template #leading>
      <slot />
    </template>
  </UiDenseActionButton>
</template>
