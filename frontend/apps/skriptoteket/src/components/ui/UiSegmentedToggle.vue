<script setup lang="ts">
/**
 * Shared segmented mode switch for mutually exclusive dense-tool modes.
 *
 * Relationships:
 * - consumed by planner/editor mode selection surfaces
 * - freezes segmented controls as a single-choice mode switch instead of pressed buttons
 */

import { computed, nextTick, onMounted, onScopeDispose, ref, watch } from "vue";

import {
  DENSE_SEGMENTED_SHELL_CLASS,
  DENSE_SEGMENTED_SUBRAIL_SHELL_CLASS,
  DENSE_SEGMENTED_WORKSPACE_SHELL_CLASS,
} from "./denseToolPrimitives";

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

const containerRef = ref<HTMLElement | null>(null);
const buttonRefs = ref<(HTMLButtonElement | null)[]>([]);

type ActiveRect = { x: number; y: number; width: number; height: number };
const activeRect = ref<ActiveRect | null>(null);

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

const containerStyle = computed(() => {
  if (props.width === "auto") {
    return {
      gridTemplateColumns: `repeat(${columnCount.value}, auto)`,
    };
  }

  return {
    gridTemplateColumns: `repeat(${columnCount.value}, minmax(0, 1fr))`,
  };
});
const equalizedButtonStyle = computed<Record<string, string> | undefined>(() => {
  if (!props.equalizeOptionWidth || props.options.length === 0) {
    return undefined;
  }

  const longestLabelLength = Math.max(...props.options.map((option) => option.label.length));
  return {
    minWidth: `${longestLabelLength + 2}ch`,
  };
});

const isCompact = computed(() => props.density === "compact");
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

  return isCompact.value
    ? "h-[24px] px-2 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none whitespace-nowrap"
    : "h-[28px] px-3 py-1 text-xs font-semibold tracking-wide whitespace-nowrap";
});

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

let resizeObserver: ResizeObserver | null = null;
let scheduledMeasureId: number | null = null;

function setButtonRef(index: number, el: HTMLButtonElement | null): void {
  buttonRefs.value[index] = el;
}

function findActiveIndex(): number {
  const index = props.options.findIndex((opt) => opt.value === props.modelValue);
  return index >= 0 ? index : 0;
}

function measureActiveRect(): void {
  const container = containerRef.value;
  if (!container) {
    activeRect.value = null;
    return;
  }

  const activeIndex = findActiveIndex();
  const button = buttonRefs.value[activeIndex];
  if (!button) {
    activeRect.value = null;
    return;
  }

  const containerBox = container.getBoundingClientRect();
  const buttonBox = button.getBoundingClientRect();

  activeRect.value = {
    x: buttonBox.left - containerBox.left - container.clientLeft,
    y: buttonBox.top - containerBox.top - container.clientTop,
    width: buttonBox.width,
    height: buttonBox.height,
  };
}

function scheduleMeasure(): void {
  if (typeof window === "undefined") {
    measureActiveRect();
    return;
  }
  if (scheduledMeasureId !== null) {
    window.cancelAnimationFrame(scheduledMeasureId);
  }
  scheduledMeasureId = window.requestAnimationFrame(() => {
    scheduledMeasureId = null;
    measureActiveRect();
  });
}

function selectOption(option: UiSegmentedToggleOption): void {
  if (props.disabled || option.disabled) return;
  if (option.value === props.modelValue) return;
  emit("update:modelValue", option.value);
}

function enabledOptions(): UiSegmentedToggleOption[] {
  return props.options.filter((option) => !props.disabled && !option.disabled);
}

function selectedIndex(): number {
  const index = props.options.findIndex((option) => option.value === props.modelValue);
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
  return `segmented-toggle-option-hint-${index}`;
}

function onOptionKeydown(event: KeyboardEvent, index: number): void {
  if (props.disabled || props.options[index]?.disabled || enabledOptions().length === 0) {
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
      selectOption(props.options[index]!);
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

const sliderStyle = computed(() => {
  if (!activeRect.value) return {};

  const insetY = 1;
  const y = activeRect.value.y + insetY;
  const height = Math.max(0, activeRect.value.height - insetY * 2);

  const transition = prefersReducedMotion()
    ? "none"
    : [
        `transform var(--huleedu-duration-fast) var(--huleedu-ease-default)`,
        `width var(--huleedu-duration-fast) var(--huleedu-ease-default)`,
        `height var(--huleedu-duration-fast) var(--huleedu-ease-default)`,
      ].join(", ");

  return {
    transform: `translate3d(${activeRect.value.x}px, ${y}px, 0)`,
    width: `${activeRect.value.width}px`,
    height: `${height}px`,
    transition,
  };
});

watch(
  () => props.modelValue,
  () => {
    void nextTick(() => scheduleMeasure());
  },
);

watch(
  () => props.options,
  () => {
    void nextTick(() => scheduleMeasure());
  },
  { deep: true },
);

onMounted(() => {
  scheduleMeasure();

  if (typeof window !== "undefined") {
    window.addEventListener("resize", scheduleMeasure, { passive: true });
  }

  if (typeof ResizeObserver !== "undefined" && containerRef.value) {
    resizeObserver = new ResizeObserver(() => scheduleMeasure());
    resizeObserver.observe(containerRef.value);
  }
});

onScopeDispose(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("resize", scheduleMeasure);
  }

  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }

  if (scheduledMeasureId !== null) {
    window.cancelAnimationFrame(scheduledMeasureId);
    scheduledMeasureId = null;
  }
});
</script>

<template>
  <div
    ref="containerRef"
    class="relative grid items-stretch"
    :class="[shellClass, widthClass]"
    :style="containerStyle"
    role="radiogroup"
    :aria-label="ariaLabel"
    data-ui="segmented-toggle"
  >
    <span
      aria-hidden="true"
      class="absolute left-0 top-0 rounded-[2px] bg-action pointer-events-none z-0 will-change-transform"
      :style="sliderStyle"
    />

    <div
      v-for="(option, index) in props.options"
      :key="option.value"
      class="relative flex"
      :title="props.disabled || option.disabled ? option.title || undefined : undefined"
      data-ui-option="segmented-toggle-option"
    >
      <button
        :ref="(el) => setButtonRef(index, el as HTMLButtonElement | null)"
        type="button"
        :disabled="props.disabled || option.disabled"
        role="radio"
        :aria-checked="option.value === props.modelValue"
        :tabindex="tabindexForOption(index)"
        :aria-describedby="optionDescriptionId(index)"
        :title="option.title || undefined"
        :data-test="option.dataTest"
        class="relative z-[2] inline-flex w-full items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-action/40 focus-visible:outline-offset-2 transition-colors duration-200"
        :class="[
          optionClass,
          index > 0 ? 'border-l border-navy/20' : '',
          option.value === props.modelValue ? 'text-button-primary-text' : 'text-navy/70 hover:text-navy',
          props.disabled || option.disabled
            ? `opacity-40 cursor-not-allowed ${
              option.value === props.modelValue ? 'hover:text-button-primary-text' : 'hover:text-navy/70'
            }`
            : '',
        ]"
        :style="equalizedButtonStyle"
        @click="selectOption(option)"
        @keydown="onOptionKeydown($event, index)"
      >
        {{ option.label }}
      </button>
      <span
        v-if="option.title"
        :id="optionDescriptionId(index)"
        class="sr-only"
      >
        {{ option.title }}
      </span>
    </div>
  </div>
</template>
