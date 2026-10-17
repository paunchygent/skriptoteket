<script setup lang="ts">
/**
 * Purpose:
 *     Provide the shared dense action button primitive.
 *
 * Relationships:
 *     - Uses denseActionButtonClass from the shared primitive contract.
 *     - Renders UiDenseSpinner while busy or when reserving the busy slot.
 *     - Forms the base for icon, menu, and compact toolbar actions.
 */

import { computed, ref, useAttrs } from "vue";

import {
  denseActionButtonClass,
  type DenseActionGroupPosition,
  type DenseActionSize,
  type DenseActionTone,
} from "../denseToolPrimitives";
import UiDenseSpinner from "./UiDenseSpinner.vue";

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

defineOptions({
  inheritAttrs: false,
});

const attrs = useAttrs();
const buttonRef = ref<null | { focus: () => void }>(null);

const buttonClass = computed(() =>
  denseActionButtonClass({
    tone: props.tone,
    size: props.size,
    active: props.active || Boolean(props.expanded),
    iconOnly: props.iconOnly,
    groupPosition: props.groupPosition,
  }),
);

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
      <slot name="leading"></slot>
    </span>
    <span v-if="!iconOnly">{{ label }}</span>
    <span
      v-if="$slots.trailing"
      class="shrink-0"
      aria-hidden="true"
    >
      <slot name="trailing"></slot>
    </span>
  </button>
</template>
