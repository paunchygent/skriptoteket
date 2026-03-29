<script setup lang="ts">
/**
 * Icon-first dense toolbar button.
 *
 * Relationships:
 * - thin convenience wrapper over `UiDenseActionButton`
 * - used for canonical icon-first actions such as undo, redo, history, and overflow
 */

import { ref } from "vue";

import type {
  DenseActionGroupPosition,
  DenseActionSize,
  DenseActionTone,
} from "./denseToolPrimitives";
import UiDenseActionButton from "./UiDenseActionButton.vue";

withDefaults(
  defineProps<{
    label: string;
    title?: string;
    ariaLabel?: string;
    disabled?: boolean;
    tone?: DenseActionTone;
    size?: DenseActionSize;
    groupPosition?: DenseActionGroupPosition;
    active?: boolean;
    expanded?: boolean;
    hasPopup?: "menu" | "dialog";
  }>(),
  {
    title: undefined,
    ariaLabel: undefined,
    disabled: false,
    tone: "default",
    size: "icon",
    groupPosition: "single",
    active: false,
    expanded: undefined,
    hasPopup: undefined,
  },
);

const actionButtonRef = ref<InstanceType<typeof UiDenseActionButton> | null>(null);

defineExpose({
  focus() {
    actionButtonRef.value?.focus?.();
  },
});
</script>

<template>
  <UiDenseActionButton
    ref="actionButtonRef"
    :label="label"
    :title="title"
    :aria-label="ariaLabel"
    :disabled="disabled"
    :tone="tone"
    :size="size"
    icon-only
    :group-position="groupPosition"
    :active="active"
    :expanded="expanded"
    :has-popup="hasPopup"
    v-bind="$attrs"
  >
    <template #leading>
      <slot />
    </template>
  </UiDenseActionButton>
</template>
