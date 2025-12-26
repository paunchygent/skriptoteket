<script setup lang="ts">
import type { components } from "../../api/openapi";
import type { ToolInputFormValue, ToolInputFormValues } from "../../composables/tools/useToolInputs";

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type ToolInputSchema = NonNullable<ToolMetadataResponse["input_schema"]>;
type ToolInputField = ToolInputSchema[number];

const props = defineProps<{
  idBase: string;
  fields: ToolInputField[];
  modelValue: ToolInputFormValues;
  errors: Record<string, string>;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: ToolInputFormValues): void;
}>();

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
  <div class="space-y-4">
    <div
      v-if="fields.length === 0"
      class="text-sm text-navy/60"
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
        class="text-xs font-semibold uppercase tracking-wide text-navy/70"
      >
        {{ field.label }}
      </label>

      <textarea
        v-if="field.kind === 'text'"
        :id="`${idBase}-input-${field.name}`"
        :value="getValue(field) as string"
        rows="4"
        class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
        @input="updateField(field.name, ($event.target as HTMLTextAreaElement).value)"
      />

      <select
        v-else-if="field.kind === 'enum'"
        :id="`${idBase}-input-${field.name}`"
        :value="getValue(field) as string"
        class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
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
        class="flex items-center gap-2 border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
      >
        <input
          :id="`${idBase}-input-${field.name}`"
          type="checkbox"
          :checked="getValue(field) === true"
          class="h-4 w-4"
          @change="updateField(field.name, ($event.target as HTMLInputElement).checked)"
        >
        <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          {{ field.label }}
        </span>
      </label>

      <input
        v-else
        :id="`${idBase}-input-${field.name}`"
        :value="getValue(field) as string"
        :inputmode="field.kind === 'integer' ? 'numeric' : field.kind === 'number' ? 'decimal' : undefined"
        type="text"
        class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
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
