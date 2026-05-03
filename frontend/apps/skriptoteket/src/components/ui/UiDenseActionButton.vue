<script setup lang="ts">
/**
 * Shared dense action button for planner and editor toolbars.
 *
 * Relationships:
 * - base primitive for icon-first, icon-led, and compact text-visible tool actions
 * - consumed by `UiDenseIconButton`, `UiDenseMenuButton`, and local toolbar/menu wrappers
 */

import { computed, ref, useAttrs } from "vue";

import {
  denseActionButtonClass,
  type DenseActionGroupPosition,
  type DenseActionSize,
  type DenseActionTone,
} from "./denseToolPrimitives";
import UiDenseSpinner from "./UiDenseSpinner.vue";

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    label: string;
    ariaLabel?: string;
    title?: string;
    disabled?: boolean;
    tone?: DenseActionTone;
    size?: DenseActionSize;
    iconOnly?: boolean;
    groupPosition?: DenseActionGroupPosition;
    active?: boolean;
    expanded?: boolean;
    hasPopup?: "menu" | "dialog";
    type?: "button" | "submit" | "reset";
    busy?: boolean;
    busyLabel?: string;
    reserveBusySlot?: boolean;
  }>(),
  {
    ariaLabel: undefined,
    title: undefined,
    disabled: false,
    tone: "default",
    size: "utility",
    iconOnly: false,
    groupPosition: "single",
    active: false,
    expanded: undefined,
    hasPopup: undefined,
    type: "button",
    busy: false,
    busyLabel: undefined,
    reserveBusySlot: false,
  },
);

const attrs = useAttrs();
const buttonRef = ref<HTMLButtonElement | null>(null);

const buttonClass = computed(() => {
  return denseActionButtonClass({
    tone: props.tone,
    size: props.size,
    active: props.active || Boolean(props.expanded),
    iconOnly: props.iconOnly,
    groupPosition: props.groupPosition,
  });
});

const resolvedAriaLabel = computed(() => {
  if (props.busy && props.busyLabel) {
    return props.busyLabel;
  }
  if (props.iconOnly) {
    return props.ariaLabel ?? props.label;
  }
  return props.ariaLabel;
});

const resolvedTitle = computed(() => {
  if (props.busy && props.busyLabel) {
    return props.busyLabel;
  }
  if (props.title) {
    return props.title;
  }
  if (props.iconOnly) {
    return props.label;
  }
  return undefined;
});

defineExpose({
  focus() {
    buttonRef.value?.focus();
  },
});
</script>

<template>
  <button
    ref="buttonRef"
    v-bind="attrs"
    :type="type"
    :class="buttonClass"
    :disabled="disabled"
    :aria-label="resolvedAriaLabel"
    :title="resolvedTitle"
    :aria-busy="busy ? 'true' : undefined"
    :aria-pressed="active || undefined"
    :aria-expanded="expanded"
    :aria-haspopup="hasPopup"
    data-ui="dense-action-button"
  >
    <span
      v-if="busy"
      class="shrink-0"
      aria-hidden="true"
    >
      <UiDenseSpinner :size="iconOnly ? 14 : 12" />
    </span>
    <span
      v-else-if="reserveBusySlot"
      class="invisible shrink-0"
      aria-hidden="true"
    >
      <UiDenseSpinner :size="iconOnly ? 14 : 12" />
    </span>
    <span
      v-else-if="$slots.leading"
      class="shrink-0"
      aria-hidden="true"
    >
      <slot name="leading" />
    </span>
    <span v-if="!iconOnly">{{ label }}</span>
    <span
      v-if="$slots.trailing"
      class="shrink-0"
      aria-hidden="true"
    >
      <slot name="trailing" />
    </span>
  </button>
</template>
