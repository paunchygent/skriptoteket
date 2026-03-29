<script setup lang="ts">
/**
 * Dense labeled toolbar toggle for compact on/off tool features.
 *
 * Relationships:
 * - complements the low-level `ToggleSwitch` with a text-visible dense-toolbar pattern
 * - used directly and as the left half of `UiDenseCompoundToggle`
 */

import { computed } from "vue";

import { IconCheck } from "../icons";
import { denseActionButtonClass, type DenseActionGroupPosition } from "./denseToolPrimitives";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    label: string;
    ariaLabel?: string;
    title?: string;
    disabled?: boolean;
    groupPosition?: DenseActionGroupPosition;
  }>(),
  {
    ariaLabel: undefined,
    title: undefined,
    disabled: false,
    groupPosition: "single",
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();

const buttonClass = computed(() => {
  return denseActionButtonClass({
    tone: "default",
    size: "utility",
    active: props.modelValue,
    iconOnly: false,
    groupPosition: props.groupPosition,
  });
});

function toggle(): void {
  if (props.disabled) {
    return;
  }
  emit("update:modelValue", !props.modelValue);
}
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :aria-label="ariaLabel ?? label"
    :title="title"
    :disabled="disabled"
    :class="buttonClass"
    data-ui="dense-toggle"
    @click="toggle"
  >
    <span
      class="grid h-3.5 w-3.5 shrink-0 place-items-center rounded-[2px] border"
      :class="modelValue ? 'border-navy bg-navy text-canvas' : 'border-navy/30 bg-white text-transparent'"
      aria-hidden="true"
    >
      <IconCheck :size="10" />
    </span>
    <span>{{ label }}</span>
  </button>
</template>
