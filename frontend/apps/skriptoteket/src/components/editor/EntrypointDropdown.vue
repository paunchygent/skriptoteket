<script setup lang="ts">
import { computed, ref, watch } from "vue";

type EntrypointDropdownProps = {
  modelValue: string;
  options: string[];
  label?: string;
  placeholder?: string;
  disabled?: boolean;
};

const CUSTOM_OPTION = "__custom__";

const props = withDefaults(defineProps<EntrypointDropdownProps>(), {
  label: "Startfunktion",
  placeholder: "run_tool",
  disabled: false,
});

const emit = defineEmits<{ (event: "update:modelValue", value: string): void }>();

const customValue = ref("");

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
    <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
      {{ label }}
    </label>
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
      <select
        :value="selectedOption"
        class="w-full sm:w-44 border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
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
        class="w-full flex-1 border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
        :placeholder="placeholder"
        :disabled="disabled"
        @input="handleCustomInput"
      >
    </div>
  </div>
</template>
