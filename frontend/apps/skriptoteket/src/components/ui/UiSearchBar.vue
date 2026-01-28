<script setup lang="ts">
import { computed } from "vue";

import { IconSearch } from "../icons";

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

const buttonClass = computed(() => {
  return props.variant === "popover"
    ? "grid place-items-center w-[32px] border-l border-navy/30 bg-canvas text-navy/70 hover:bg-canvas/70 hover:text-navy shadow-none"
    : "grid place-items-center w-[44px] border-l border-navy bg-canvas text-navy/70 hover:bg-canvas/70 hover:text-navy shadow-none";
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
      <button
        v-if="showButton"
        type="button"
        :class="buttonClass"
        :disabled="disabled || isBusy || buttonDisabled"
        :aria-label="ariaLabel ?? 'Sök'"
        @click="onSubmit"
      >
        <IconSearch :size="16" />
      </button>
    </div>
  </div>
</template>
