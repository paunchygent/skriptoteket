<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

type UiMultiEnumField = components["schemas"]["UiMultiEnumField"];

const props = defineProps<{
  field: UiMultiEnumField;
  idBase: string;
  modelValue: string[];
  density?: "default" | "compact";
}>();

const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();

const isCompact = computed(() => props.density === "compact");

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
  <fieldset
    :class="[isCompact ? 'space-y-1.5' : 'space-y-2']"
  >
    <legend
      :class="[
        'font-semibold',
        isCompact ? 'text-[10px] uppercase tracking-wide text-navy/60' : 'text-sm text-navy',
      ]"
    >
      {{ field.label }}
    </legend>

    <div
      :class="[isCompact ? 'space-y-1.5' : 'space-y-2']"
    >
      <div
        v-for="(opt, index) in field.options"
        :key="opt.value"
        :class="[isCompact ? 'flex items-center gap-2' : 'flex items-start gap-3']"
      >
        <input
          :id="`${idBase}-opt-${index}`"
          type="checkbox"
          :value="opt.value"
          :checked="modelValue.includes(opt.value)"
          :class="[
            'border border-navy accent-burgundy',
            isCompact ? 'h-3.5 w-3.5' : 'mt-1 h-4 w-4',
          ]"
          @change="onChange"
        >
        <label
          :for="`${idBase}-opt-${index}`"
          :class="[isCompact ? 'text-[11px] text-navy' : 'text-sm text-navy']"
        >
          {{ opt.label }}
        </label>
      </div>
    </div>
  </fieldset>
</template>
