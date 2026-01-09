<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";
import type { ToolInputFormValue, ToolInputFormValues } from "../../composables/tools/useToolInputs";

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type ToolInputSchema = NonNullable<ToolMetadataResponse["input_schema"]>;
type ToolInputField = ToolInputSchema[number];

const props = withDefaults(defineProps<{
  idBase: string;
  fields: ToolInputField[];
  modelValue: ToolInputFormValues;
  errors: Record<string, string>;
  density?: "default" | "compact";
}>(), {
  density: "default",
});

const emit = defineEmits<{
  (event: "update:modelValue", value: ToolInputFormValues): void;
}>();

const isCompact = computed(() => props.density === "compact");

function defaultValue(field: ToolInputField): ToolInputFormValue {
  if (field.kind === "boolean") return false;
  return "";
}

function getValue(field: ToolInputField): ToolInputFormValue {
  return props.modelValue[field.name] ?? defaultValue(field);
}

function updateField(name: string, value: ToolInputFormValue): void {
  emit("update:modelValue", {
    ...props.modelValue,
    [name]: value,
  });
}
</script>

<template>
  <div :class="[isCompact ? 'space-y-3' : 'space-y-4']">
    <div
      v-if="fields.length === 0"
      :class="[isCompact ? 'text-[11px] text-navy/60' : 'text-sm text-navy/60']"
    >
      Inga indata krävs.
    </div>

    <div
      v-for="field in fields"
      :key="field.name"
      class="space-y-1"
    >
      <label
        v-if="field.kind !== 'boolean'"
        :for="`${idBase}-input-${field.name}`"
        :class="[
          isCompact
            ? 'text-[10px] font-semibold uppercase tracking-wide text-navy/60'
            : 'text-xs font-semibold uppercase tracking-wide text-navy/70',
        ]"
      >
        {{ field.label }}
      </label>

      <textarea
        v-if="field.kind === 'text'"
        :id="`${idBase}-input-${field.name}`"
        :value="getValue(field) as string"
        rows="4"
        :class="[
          'w-full bg-white text-navy',
          isCompact
            ? 'border border-navy/30 px-2.5 py-1.5 text-[11px] shadow-none leading-snug'
            : 'border border-navy px-3 py-2 text-sm shadow-brutal-sm',
        ]"
        @input="updateField(field.name, ($event.target as HTMLTextAreaElement).value)"
      />

      <select
        v-else-if="field.kind === 'enum'"
        :id="`${idBase}-input-${field.name}`"
        :value="getValue(field) as string"
        :class="[
          'w-full bg-white text-navy',
          isCompact
            ? 'h-[28px] border border-navy/30 px-2.5 text-[11px] shadow-none leading-none'
            : 'border border-navy px-3 py-2 text-sm shadow-brutal-sm',
        ]"
        @change="updateField(field.name, ($event.target as HTMLSelectElement).value)"
      >
        <option value="">
          Välj...
        </option>
        <option
          v-for="option in field.options"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>

      <label
        v-else-if="field.kind === 'boolean'"
        :class="[
          'flex items-center gap-2 bg-white text-navy',
          isCompact
            ? 'border border-navy/30 px-2.5 py-1.5 text-[11px] shadow-none'
            : 'border border-navy px-3 py-2 text-sm shadow-brutal-sm',
        ]"
      >
        <input
          :id="`${idBase}-input-${field.name}`"
          type="checkbox"
          :checked="getValue(field) === true"
          :class="[isCompact ? 'h-3.5 w-3.5' : 'h-4 w-4']"
          @change="updateField(field.name, ($event.target as HTMLInputElement).checked)"
        >
        <span
          :class="[
            isCompact
              ? 'text-[10px] font-semibold uppercase tracking-wide text-navy/60'
              : 'text-xs font-semibold uppercase tracking-wide text-navy/70',
          ]"
        >
          {{ field.label }}
        </span>
      </label>

      <input
        v-else
        :id="`${idBase}-input-${field.name}`"
        :value="getValue(field) as string"
        :inputmode="field.kind === 'integer' ? 'numeric' : field.kind === 'number' ? 'decimal' : undefined"
        type="text"
        :class="[
          'w-full bg-white text-navy',
          isCompact
            ? 'h-[28px] border border-navy/30 px-2.5 text-[11px] shadow-none leading-none'
            : 'border border-navy px-3 py-2 text-sm shadow-brutal-sm',
        ]"
        @input="updateField(field.name, ($event.target as HTMLInputElement).value)"
      >

      <p
        v-if="errors[field.name]"
        class="text-xs font-semibold text-burgundy"
      >
        {{ errors[field.name] }}
      </p>
    </div>
  </div>
</template>
