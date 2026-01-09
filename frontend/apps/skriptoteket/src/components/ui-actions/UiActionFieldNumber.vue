<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

type UiNumberField = components["schemas"]["UiNumberField"];

const props = defineProps<{ field: UiNumberField; id: string; modelValue: string; density?: "default" | "compact" }>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const isCompact = computed(() => props.density === "compact");

function onInput(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  emit("update:modelValue", target?.value ?? "");
}
</script>

<template>
  <div class="space-y-1">
    <label
      :class="[
        'block font-semibold',
        isCompact
          ? 'text-[10px] uppercase tracking-wide text-navy/60'
          : 'text-sm text-navy',
      ]"
      :for="id"
    >
      {{ field.label }}
    </label>
    <input
      :id="id"
      type="number"
      step="any"
      inputmode="decimal"
      :value="modelValue"
      :class="[
        'w-full bg-white text-navy placeholder:text-navy/40',
        isCompact
          ? 'h-[28px] border border-navy/30 px-2.5 text-[11px] shadow-none leading-none'
          : 'border border-navy px-3 py-2 shadow-brutal-sm',
      ]"
      @input="onInput"
    >
  </div>
</template>
