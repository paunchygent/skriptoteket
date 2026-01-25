<script setup lang="ts">
import { computed, nextTick, onMounted, onScopeDispose, ref, watch } from "vue";

export type UiSegmentedToggleOption = {
  value: string;
  label: string;
  disabled?: boolean;
  title?: string;
};

const props = withDefaults(
  defineProps<{
    modelValue: string;
    options: UiSegmentedToggleOption[];
    ariaLabel?: string;
    density?: "default" | "compact";
    disabled?: boolean;
    columns?: number;
    width?: "responsive" | "full" | "auto";
  }>(),
  {
    ariaLabel: undefined,
    density: "default",
    disabled: false,
    columns: undefined,
    width: "responsive",
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
  if (props.options.length <= 2) {
    return Math.max(1, props.options.length);
  }
  return 2;
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
  return {
    gridTemplateColumns: `repeat(${columnCount.value}, minmax(0, 1fr))`,
  };
});

const isCompact = computed(() => props.density === "compact");

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
    class="relative grid items-stretch rounded-[4px] border border-navy/15 bg-canvas/50 p-0.5"
    :class="widthClass"
    :style="containerStyle"
    role="group"
    :aria-label="ariaLabel"
    data-ui="segmented-toggle"
  >
    <!-- Background Separators (The navy fill slides under these) -->
    <div
      aria-hidden="true"
      class="absolute inset-0 grid pointer-events-none z-[1]"
      :style="containerStyle"
    >
      <div
        v-for="i in columnCount - 1"
        :key="i"
        class="h-full border-r border-navy/20 last:border-r-0"
        :style="{ gridColumn: i }"
      />
    </div>

    <span
      aria-hidden="true"
      class="absolute left-0 top-0 rounded-[2px] bg-navy pointer-events-none z-0 will-change-transform"
      :style="sliderStyle"
    />

    <button
      v-for="(option, index) in props.options"
      :key="option.value"
      :ref="(el) => setButtonRef(index, el as HTMLButtonElement | null)"
      type="button"
      :disabled="props.disabled || option.disabled"
      :aria-pressed="option.value === props.modelValue"
      :title="option.title || undefined"
      class="relative z-[2] inline-flex w-full items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2 transition-colors duration-200"
      :class="[
        isCompact
          ? 'h-[24px] px-2 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none whitespace-nowrap'
          : 'h-[28px] px-3 py-1 text-xs font-semibold tracking-wide whitespace-nowrap',
        option.value === props.modelValue ? 'text-canvas' : 'text-navy/70 hover:text-navy',
        props.disabled || option.disabled ? 'opacity-40 cursor-not-allowed hover:text-navy/70' : '',
      ]"
      @click="selectOption(option)"
    >
      {{ option.label }}
    </button>
  </div>
</template>
