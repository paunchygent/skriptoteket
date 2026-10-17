<script setup lang="ts">
/**
 * Text-visible dense menu trigger with canonical disclosure affordance.
 *
 * Relationships:
 * - wrapper over `UiDenseActionButton`
 * - used by editor save/open and tool menus
 */

import { ref } from "vue";

import { UiGlyph } from "./shared";
import type { DenseActionTone } from "./shared/denseToolPrimitives";
import UiDenseActionButton from "./shared/components/UiDenseActionButton.vue";

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
      <UiGlyph
        meaning="open-list"
        :size="12"
        :stroke-width="2.5"
      />
    </template>
  </UiDenseActionButton>
</template>
