<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiIntegerField = components["schemas"]["UiIntegerField"];

defineProps<{ field: UiIntegerField; id: string; modelValue: string }>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

function onInput(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  emit("update:modelValue", target?.value ?? "");
}
</script>

<template>
  <div class="space-y-1">
    <label
      class="block text-sm font-semibold text-navy"
      :for="id"
    >
      {{ field.label }}
    </label>
    <input
      :id="id"
      type="number"
      step="1"
      inputmode="numeric"
      :value="modelValue"
      class="w-full px-3 py-2 border border-navy bg-white shadow-brutal-sm text-navy placeholder:text-navy/40"
      @input="onInput"
    >
  </div>
</template>

