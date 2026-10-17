<script setup lang="ts">
/**
 * Purpose:
 *     Provide an icon-only dense action button with dense or touch geometry.
 *
 * Relationships:
 *     - Wraps UiDenseActionButton.
 *     - Reuses the shared dense-action primitive contract.
 */

import type { DenseActionSize, DenseActionTone } from "../denseToolPrimitives";
import UiDenseActionButton from "./UiDenseActionButton.vue";

withDefaults(
  defineProps<{
    label: string;
    title?: string;
    disabled?: boolean;
    tone?: DenseActionTone;
    size?: Extract<DenseActionSize, "icon" | "touch">;
    active?: boolean;
    type?: "button" | "submit" | "reset";
  }>(),
  {
    title: undefined,
    disabled: false,
    tone: "default",
    size: "icon",
    active: false,
    type: "button",
  },
);
</script>

<template>
  <UiDenseActionButton
    :label="label"
    :title="title"
    :disabled="disabled"
    :tone="tone"
    :active="active"
    :type="type"
    :size="size"
    icon-only
  >
    <template #leading>
      <slot></slot>
    </template>
  </UiDenseActionButton>
</template>
