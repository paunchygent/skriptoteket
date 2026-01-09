<script setup lang="ts">
import { computed, ref, watch } from "vue";

type EntrypointDropdownProps = {
  id?: string;
  modelValue: string;
  options: string[];
  label?: string;
  placeholder?: string;
  disabled?: boolean;
};

const CUSTOM_OPTION = "__custom__";

const props = withDefaults(defineProps<EntrypointDropdownProps>(), {
  id: "tool-entrypoint",
  label: "Startfunktion",
  placeholder: "run_tool",
  disabled: false,
});

const emit = defineEmits<{ (event: "update:modelValue", value: string): void }>();

const customValue = ref("");

const selectId = computed(() => props.id);
const helpId = computed(() => `${selectId.value}-help`);
const helpText =
  "Måste vara en funktion i skriptet som tar (input_dir, output_dir).";

const selectedOption = computed(() => {
  return props.options.includes(props.modelValue) ? props.modelValue : CUSTOM_OPTION;
});

const isCustom = computed(() => selectedOption.value === CUSTOM_OPTION);

function handleSelectChange(event: Event): void {
  const target = event.target as HTMLSelectElement | null;
  if (!target) return;

  const value = target.value;
  if (value === CUSTOM_OPTION) {
    if (props.options.includes(props.modelValue)) {
      customValue.value = props.modelValue;
    }
    return;
  }

  emit("update:modelValue", value);
}

function handleCustomInput(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  customValue.value = target.value;
  emit("update:modelValue", target.value);
}

watch(
  () => props.modelValue,
  (value) => {
    if (!props.options.includes(value)) {
      customValue.value = value;
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="space-y-2">
    <div class="relative inline-flex items-center gap-2">
      <label
        class="text-[10px] font-semibold uppercase tracking-wide text-navy/60"
        :for="selectId"
      >
        {{ label }}
      </label>
      <div class="relative group">
        <button
          type="button"
          class="inline-flex h-3.5 w-3.5 items-center justify-center text-[9px] font-semibold leading-none text-navy/50 hover:text-navy self-center -translate-y-[3px]"
          aria-label="Visa hjälp"
        >
          ?
        </button>
        <div
          :id="helpId"
          class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy/30 bg-white text-navy px-3 py-2 text-[11px] opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
          role="tooltip"
        >
          <span class="text-[11px] text-navy/80">
            {{ helpText }}
          </span>
        </div>
      </div>
    </div>
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
      <select
        :id="selectId"
        :value="selectedOption"
        :aria-describedby="helpId"
        class="w-full sm:w-44 h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none"
        :disabled="disabled"
        @change="handleSelectChange"
      >
        <option
          v-for="option in options"
          :key="option"
          :value="option"
        >
          {{ option }}
        </option>
        <option :value="CUSTOM_OPTION">Eget…</option>
      </select>

      <input
        v-if="isCustom"
        :value="customValue"
        type="text"
        :aria-describedby="helpId"
        class="w-full flex-1 h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none"
        :placeholder="placeholder"
        :disabled="disabled"
        @input="handleCustomInput"
      >
    </div>
  </div>
</template>
