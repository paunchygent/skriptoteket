<script setup lang="ts">
/**
 * Compact icon-first toolbar button for planner action rows.
 *
 * Relationships:
 * - thin planner-facing adapter over the shared `UiDenseIconButton` primitive
 * - preserves existing planner call sites while the shared dense-tool layer settles
 */

import { UiDenseIconButton } from "../../../components/ui";
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
  <UiDenseIconButton
    :label="label"
    :title="title ?? label"
    :disabled="disabled"
    :size="size"
    :group-position="groupPosition"
  >
    <slot />
  </UiDenseIconButton>
</template>
