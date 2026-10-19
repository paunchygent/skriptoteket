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
 *     - Uses roving radio focus with arrow, Home and End selection, skipping
 *       disabled options, and links option titles as accessible guidance.
 */

import { computed, onBeforeUnmount, ref, useId, watch } from "vue";

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

type FocusableButton = Element & { focus: () => void };
const buttonRefs = ref<(FocusableButton | null)[]>([]);
const descriptionId = useId();

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

function isFocusableButton(element: unknown): element is FocusableButton {
  return element instanceof Element && "focus" in element && typeof element.focus === "function";
}

function setButtonRef(index: number, element: unknown): void {
  buttonRefs.value[index] = isFocusableButton(element) ? element : null;
}

function enabledOptions(): UiSegmentedToggleOption[] {
  return props.options.filter((option) => !props.disabled && !option.disabled);
}

function selectedIndex(): number {
  const index = props.options.findIndex(
    (option) => option.value === props.modelValue && !option.disabled,
  );
  if (index >= 0) {
    return index;
  }
  return props.options.findIndex((option) => !option.disabled);
}

function tabindexForOption(index: number): number {
  if (props.disabled || props.options[index]?.disabled) {
    return -1;
  }
  return index === selectedIndex() ? 0 : -1;
}

function focusOption(index: number): void {
  buttonRefs.value[index]?.focus();
}

function nextEnabledIndex(fromIndex: number, direction: 1 | -1): number {
  const total = props.options.length;
  for (let step = 1; step <= total; step += 1) {
    const candidate = (fromIndex + step * direction + total) % total;
    if (!props.options[candidate]?.disabled) {
      return candidate;
    }
  }
  return fromIndex;
}

function firstEnabledIndex(): number {
  return props.options.findIndex((option) => !option.disabled);
}

function lastEnabledIndex(): number {
  for (let index = props.options.length - 1; index >= 0; index -= 1) {
    if (!props.options[index]?.disabled) {
      return index;
    }
  }
  return -1;
}

function optionDescriptionId(index: number): string | undefined {
  const option = props.options[index];
  if (!option?.title) {
    return undefined;
  }
  return `${descriptionId}-option-hint-${index}`;
}

function onOptionKeydown(event: KeyboardEvent, index: number): void {
  const option = props.options[index];
  if (!option || props.disabled || option.disabled || enabledOptions().length === 0) {
    return;
  }

  let targetIndex = index;
  switch (event.key) {
    case "ArrowRight":
    case "ArrowDown":
      targetIndex = nextEnabledIndex(index, 1);
      break;
    case "ArrowLeft":
    case "ArrowUp":
      targetIndex = nextEnabledIndex(index, -1);
      break;
    case "Home":
      targetIndex = firstEnabledIndex();
      break;
    case "End":
      targetIndex = lastEnabledIndex();
      break;
    case " ":
    case "Enter":
      selectOption(option);
      return;
    default:
      return;
  }

  event.preventDefault();
  const nextOption = props.options[targetIndex];
  if (!nextOption) {
    return;
  }
  focusOption(targetIndex);
  selectOption(nextOption);
}

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
    <template
      v-for="(option, index) in options"
      :key="option.value"
    >
      <button
        :ref="(element) => setButtonRef(index, element)"
        type="button"
        role="radio"
        :aria-checked="option.value === modelValue"
        :tabindex="tabindexForOption(index)"
        :aria-describedby="optionDescriptionId(index)"
        :disabled="disabled || option.disabled"
        :title="option.title"
        :data-test="option.dataTest"
        :class="[
          optionClass,
          'rounded-[4px] border text-navy transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-1 disabled:cursor-not-allowed disabled:opacity-50',
          option.value === modelValue ? 'border-navy/20 bg-white' : 'border-transparent bg-transparent hover:bg-white/70',
        ]"
        @click="selectOption(option)"
        @keydown="onOptionKeydown($event, index)"
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
      <span
        v-if="option.title"
        :id="optionDescriptionId(index)"
        class="sr-only"
      >
        {{ option.title }}
      </span>
    </template>
  </div>
</template>
