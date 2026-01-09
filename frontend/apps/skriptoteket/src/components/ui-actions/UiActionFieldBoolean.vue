<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

type UiBooleanField = components["schemas"]["UiBooleanField"];

const props = defineProps<{ field: UiBooleanField; id: string; modelValue: boolean; density?: "default" | "compact" }>();

const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();

const isCompact = computed(() => props.density === "compact");

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  emit("update:modelValue", Boolean(target?.checked));
}
</script>

<template>
  <div :class="[isCompact ? 'flex items-center gap-2' : 'flex items-start gap-3']">
    <input
      :id="id"
      type="checkbox"
      :checked="modelValue"
      :class="[
        'border border-navy accent-burgundy',
        isCompact ? 'h-3.5 w-3.5' : 'mt-1 h-4 w-4',
      ]"
      @change="onChange"
    >
    <label
      :for="id"
      :class="[
        isCompact ? 'text-[11px] text-navy' : 'text-sm text-navy',
      ]"
    >
      {{ field.label }}
    </label>
  </div>
</template>
