<script setup lang="ts">
/**
 * Shared icon tile segmented control.
 *
 * Domain purpose:
 *   Present mutually exclusive, icon-supported output or mode choices in dense
 *   teacher workspaces without duplicating segmented tile styling per app.
 *
 * Relationships:
 *   - Extends the shared dense segmented-control family for larger option
 *     tiles.
 *   - Consumed by route-visible curated apps with icon-led choice cards.
 */

import { computed, toRaw, useAttrs, type Component } from "vue";

export type UiSegmentedTileToggleOption = {
  value: string;
  label: string;
  ariaLabel?: string;
  icon?: Component;
  disabled?: boolean;
  dataTest?: string;
};

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    modelValue: string;
    options: UiSegmentedTileToggleOption[];
    ariaLabel?: string;
    disabled?: boolean;
    columns?: number;
  }>(),
  {
    ariaLabel: undefined,
    disabled: false,
    columns: undefined,
  },
);

const attrs = useAttrs();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const resolvedAriaLabel = computed(() => {
  if (props.ariaLabel) {
    return props.ariaLabel;
  }

  const ariaLabel = attrs["aria-label"];
  return typeof ariaLabel === "string" ? ariaLabel : undefined;
});

function selectOption(option: UiSegmentedTileToggleOption): void {
  if (props.disabled || option.disabled) {
    return;
  }
  emit("update:modelValue", option.value);
}

function optionIcon(option: UiSegmentedTileToggleOption): Component | null {
  return option.icon ? toRaw(option.icon) : null;
}
</script>

<template>
  <div
    class="ui-segmented-tile-toggle"
    role="radiogroup"
    :aria-label="resolvedAriaLabel"
    :style="{ gridTemplateColumns: `repeat(${props.columns ?? props.options.length}, minmax(0, 1fr))` }"
    data-ui="segmented-tile-toggle"
  >
    <button
      v-for="option in props.options"
      :key="option.value"
      class="ui-segmented-tile-toggle__option"
      :class="{ 'ui-segmented-tile-toggle__option--active': option.value === props.modelValue }"
      type="button"
      role="radio"
      :aria-label="option.ariaLabel"
      :aria-checked="option.value === props.modelValue"
      :disabled="props.disabled || option.disabled"
      :data-test="option.dataTest"
      @click="selectOption(option)"
    >
      <component
        :is="optionIcon(option)"
        v-if="option.icon"
        :size="22"
        aria-hidden="true"
      />
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.ui-segmented-tile-toggle {
  display: grid;
  border: 1px solid color-mix(in srgb, var(--color-navy) 40%, transparent);
  border-radius: 4px;
  overflow: hidden;
}

.ui-segmented-tile-toggle__option {
  min-height: 5.75rem;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 0.6rem;
  padding: 0 0.75rem;
  border: 0;
  border-right: 1px solid color-mix(in srgb, var(--color-navy) 30%, transparent);
  border-radius: 0;
  background: var(--color-panel);
  color: var(--color-navy);
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1.2;
  text-align: center;
}

.ui-segmented-tile-toggle__option:last-child {
  border-right: 0;
}

.ui-segmented-tile-toggle__option--active {
  background: color-mix(in srgb, var(--color-action) 5%, transparent);
  box-shadow: inset 0 0 0 2px var(--color-action);
}
</style>
