<script setup lang="ts">
import { computed } from "vue";

import { UiDenseIconButton, UiGlyph } from "./shared";

type UiSearchBarVariant = "panel" | "popover";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    label?: string;
    placeholder?: string;
    ariaLabel?: string;
    variant?: UiSearchBarVariant;
    disabled?: boolean;
    isBusy?: boolean;
    showButton?: boolean;
    buttonDisabled?: boolean;
  }>(),
  {
    label: undefined,
    placeholder: "Sök…",
    ariaLabel: undefined,
    variant: "panel",
    disabled: false,
    isBusy: false,
    showButton: true,
    buttonDisabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
  submit: [];
}>();

const containerClass = computed(() => {
  return props.variant === "popover"
    ? "flex items-stretch border border-navy/30 bg-white shadow-none"
    : "flex items-stretch border border-navy bg-white shadow-none";
});

const inputClass = computed(() => {
  return props.variant === "popover"
    ? "flex-1 min-w-0 h-[28px] px-2.5 bg-transparent text-[11px] text-navy outline-none"
    : "flex-1 min-w-0 h-[38px] px-3 bg-transparent text-sm text-navy outline-none";
});

function onInput(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  emit("update:modelValue", target.value);
}

function onSubmit(): void {
  emit("submit");
}
</script>

<template>
  <div class="space-y-1">
    <label
      v-if="label"
      class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
    >
      {{ label }}
    </label>
    <div :class="containerClass">
      <input
        :value="modelValue"
        type="search"
        :placeholder="placeholder"
        :aria-label="ariaLabel ?? label ?? 'Sök'"
        :class="inputClass"
        :disabled="disabled"
        @input="onInput"
        @keydown.enter.prevent="onSubmit"
      >
      <UiDenseIconButton
        v-if="showButton"
        type="button"
        size="icon"
        :disabled="disabled || isBusy || buttonDisabled"
        :label="ariaLabel ?? 'Sök'"
        @click="onSubmit"
      >
        <UiGlyph
          meaning="search"
          :size="16"
          :stroke-width="2.5"
        />
      </UiDenseIconButton>
    </div>
  </div>
</template>
