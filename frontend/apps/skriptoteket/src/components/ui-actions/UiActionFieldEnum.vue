<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiEnumField = components["schemas"]["UiEnumField"];

defineProps<{ field: UiEnumField; idBase: string; modelValue: string }>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  emit("update:modelValue", target?.value ?? "");
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
          type="radio"
          :name="idBase"
          :value="opt.value"
          :checked="modelValue === opt.value"
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
