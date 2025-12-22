<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiBooleanField = components["schemas"]["UiBooleanField"];

defineProps<{ field: UiBooleanField; id: string; modelValue: boolean }>();

const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  emit("update:modelValue", Boolean(target?.checked));
}
</script>

<template>
  <div class="flex items-start gap-3">
    <input
      :id="id"
      type="checkbox"
      :checked="modelValue"
      class="mt-1 h-4 w-4 border border-navy accent-burgundy"
      @change="onChange"
    >
    <label
      :for="id"
      class="text-sm text-navy"
    >
      {{ field.label }}
    </label>
  </div>
</template>

