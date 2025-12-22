<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiMultiEnumField = components["schemas"]["UiMultiEnumField"];

const props = defineProps<{ field: UiMultiEnumField; idBase: string; modelValue: string[] }>();

const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();

function onToggle(value: string, checked: boolean): void {
  const next = checked
    ? Array.from(new Set([...props.modelValue, value]))
    : props.modelValue.filter((item) => item !== value);
  emit("update:modelValue", next);
}

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  onToggle(target.value, target.checked);
}
</script>

<template>
  <fieldset class="space-y-2">
    <legend class="text-sm font-semibold text-navy">
      {{ field.label }}
    </legend>

    <div class="space-y-2">
      <div
        v-for="(opt, index) in field.options"
        :key="opt.value"
        class="flex items-start gap-3"
      >
        <input
          :id="`${idBase}-opt-${index}`"
          type="checkbox"
          :value="opt.value"
          :checked="modelValue.includes(opt.value)"
          class="mt-1 h-4 w-4 border border-navy accent-burgundy"
          @change="onChange"
        >
        <label
          :for="`${idBase}-opt-${index}`"
          class="text-sm text-navy"
        >
          {{ opt.label }}
        </label>
      </div>
    </div>
  </fieldset>
</template>

