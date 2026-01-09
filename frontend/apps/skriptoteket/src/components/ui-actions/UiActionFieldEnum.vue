<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

type UiEnumField = components["schemas"]["UiEnumField"];

const props = defineProps<{ field: UiEnumField; idBase: string; modelValue: string; density?: "default" | "compact" }>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const isCompact = computed(() => props.density === "compact");

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  emit("update:modelValue", target?.value ?? "");
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
          type="radio"
          :name="idBase"
          :value="opt.value"
          :checked="modelValue === opt.value"
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
