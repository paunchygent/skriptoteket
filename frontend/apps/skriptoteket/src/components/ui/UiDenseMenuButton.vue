<script setup lang="ts">
/**
 * Text-visible dense menu trigger with canonical disclosure affordance.
 *
 * Relationships:
 * - wrapper over `UiDenseActionButton`
 * - used by editor save/open and tool menus
 */

import { ref } from "vue";

import { IconArrow } from "../icons";
import type { DenseActionTone } from "./denseToolPrimitives";
import UiDenseActionButton from "./UiDenseActionButton.vue";

withDefaults(
  defineProps<{
    label: string;
    title?: string;
    disabled?: boolean;
    tone?: DenseActionTone;
    expanded?: boolean;
  }>(),
  {
    title: undefined,
    disabled: false,
    tone: "default",
    expanded: false,
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
    :disabled="disabled"
    :tone="tone"
    has-popup="menu"
    :expanded="expanded"
    v-bind="$attrs"
  >
    <template
      v-if="$slots.leading"
      #leading
    >
      <slot name="leading" />
    </template>
    <template #trailing>
      <IconArrow
        :size="12"
        direction="down"
      />
    </template>
  </UiDenseActionButton>
</template>
