<script setup lang="ts">
/**
 * Purpose:
 *     Provide a shared segmented toggle for mutually exclusive modes.
 *
 * Relationships:
 *     - Uses dense segmented shell constants from denseToolPrimitives.
 *     - Keeps mode switches semantic, keyboard reachable, and layout stable.
 *     - equalizeOptionWidth measures option labels with a ResizeObserver only
 *       while enabled and gives every option the widest label width.
 */

import { computed, onBeforeUnmount, ref, watch } from "vue";

import {
  DENSE_SEGMENTED_SHELL_CLASS,
  DENSE_SEGMENTED_SUBRAIL_SHELL_CLASS,
  DENSE_SEGMENTED_WORKSPACE_SHELL_CLASS,
} from "../denseToolPrimitives";

export type UiSegmentedToggleOption = {
  value: string;
  label: string;
  disabled?: boolean;
  title?: string;
  dataTest?: string;
};

const props = withDefaults(
  defineProps<{
    modelValue: string;
    options: UiSegmentedToggleOption[];
    ariaLabel?: string;
    density?: "default" | "compact";
    variant?: "default" | "subrail" | "workspace";
    disabled?: boolean;
    columns?: number;
    width?: "responsive" | "full" | "auto";
    equalizeOptionWidth?: boolean;
  }>(),
  {
    ariaLabel: undefined,
    density: "default",
    variant: "default",
    disabled: false,
    columns: undefined,
    width: "responsive",
    equalizeOptionWidth: false,
  },
);

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const columnCount = computed(() => {
  if (props.columns && props.columns > 0) {
    return Math.min(props.columns, Math.max(1, props.options.length));
  }
  return Math.max(1, props.options.length);
});

const widthClass = computed(() => {
  switch (props.width) {
    case "full":
      return "w-full";
    case "auto":
      return "w-auto";
    default:
      return "w-full sm:w-auto";
  }
});

const containerStyle = computed(() => ({
  gridTemplateColumns:
    props.width === "auto"
      ? `repeat(${columnCount.value}, auto)`
      : `repeat(${columnCount.value}, minmax(0, 1fr))`,
}));

const shellClass = computed(() => {
  switch (props.variant) {
    case "subrail":
      return DENSE_SEGMENTED_SUBRAIL_SHELL_CLASS;
    case "workspace":
      return DENSE_SEGMENTED_WORKSPACE_SHELL_CLASS;
    default:
      return DENSE_SEGMENTED_SHELL_CLASS;
  }
});

const optionClass = computed(() => {
  if (props.variant === "workspace") {
    return "h-[40px] px-4 text-[12px] font-semibold uppercase tracking-[0.12em] leading-none whitespace-nowrap";
  }
  if (props.variant === "subrail") {
    return "h-[34px] px-3 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none whitespace-nowrap";
  }
  return props.density === "compact"
    ? "h-[24px] px-2 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none whitespace-nowrap"
    : "h-[28px] px-3 py-1 text-xs font-semibold tracking-wide whitespace-nowrap";
});

const labelElements = new Map<number, Element>();
const equalizedLabelWidth = ref<number | null>(null);
let labelObserver: ResizeObserver | null = null;

const equalizedLabelStyle = computed(() =>
  equalizedLabelWidth.value === null ? undefined : { minWidth: `${equalizedLabelWidth.value}px` },
);

function measureLabels(): void {
  let widest = 0;
  for (const element of labelElements.values()) {
    widest = Math.max(widest, element.getBoundingClientRect().width);
  }
  equalizedLabelWidth.value = widest > 0 ? Math.ceil(widest) : null;
}

function stopLabelObservation(): void {
  labelObserver?.disconnect();
  labelObserver = null;
  equalizedLabelWidth.value = null;
}

function setLabelElement(index: number, element: unknown): void {
  if (element instanceof Element) {
    labelElements.set(index, element);
    labelObserver?.observe(element);
    return;
  }
  const previous = labelElements.get(index);
  if (previous) {
    labelObserver?.unobserve(previous);
    labelElements.delete(index);
  }
}

watch(
  () => props.equalizeOptionWidth,
  (enabled) => {
    stopLabelObservation();
    if (!enabled || typeof ResizeObserver === "undefined") {
      return;
    }
    labelObserver = new ResizeObserver(measureLabels);
    for (const element of labelElements.values()) {
      labelObserver.observe(element);
    }
  },
  { immediate: true, flush: "post" },
);

onBeforeUnmount(stopLabelObservation);

function selectOption(option: UiSegmentedToggleOption): void {
  if (props.disabled || option.disabled || option.value === props.modelValue) {
    return;
  }
  emit("update:modelValue", option.value);
}
</script>

<template>
  <div
    :class="[shellClass, widthClass, 'grid gap-0']"
    :style="containerStyle"
    role="radiogroup"
    :aria-label="ariaLabel"
    data-ui="segmented-toggle"
  >
    <button
      v-for="(option, index) in options"
      :key="option.value"
      type="button"
      role="radio"
      :aria-checked="option.value === modelValue"
      :disabled="disabled || option.disabled"
      :title="option.title"
      :data-test="option.dataTest"
      :class="[
        optionClass,
        'rounded-[4px] border text-navy transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-1 disabled:cursor-not-allowed disabled:opacity-50',
        option.value === modelValue ? 'border-navy/20 bg-white' : 'border-transparent bg-transparent hover:bg-white/70',
      ]"
      @click="selectOption(option)"
    >
      <span
        v-if="equalizeOptionWidth"
        class="inline-block text-center"
        :style="equalizedLabelStyle"
      >
        <span
          :ref="(element) => setLabelElement(index, element)"
          class="inline-block"
        >{{ option.label }}</span>
      </span>
      <template v-else>
        {{ option.label }}
      </template>
    </button>
  </div>
</template>
