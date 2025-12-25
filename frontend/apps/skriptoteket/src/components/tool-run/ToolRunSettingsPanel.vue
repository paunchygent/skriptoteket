<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import UiActionFieldRenderer from "../ui-actions/UiActionFieldRenderer.vue";

type ToolSettingsResponse = components["schemas"]["ToolSettingsResponse"];
type SettingsField = NonNullable<ToolSettingsResponse["settings_schema"]>[number];
type SettingsFieldKind = SettingsField["kind"];

type FieldValue = string | boolean | string[];
type SettingsFormValues = Record<string, FieldValue>;

const props = defineProps<{
  idBase: string;
  schema: SettingsField[];
  modelValue: SettingsFormValues;
  isLoading: boolean;
  isSaving: boolean;
  errorMessage: string | null;
  successMessage: string | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: SettingsFormValues];
  save: [];
}>();

const fieldIdBase = computed(() => `${props.idBase}-settings`);

function defaultValueForKind(kind: SettingsFieldKind): FieldValue {
  switch (kind) {
    case "boolean":
      return false;
    case "multi_enum":
      return [];
    default:
      return "";
  }
}

function valueForField(field: SettingsField): FieldValue {
  return props.modelValue[field.name] ?? defaultValueForKind(field.kind);
}

function updateField(name: string, value: FieldValue): void {
  emit("update:modelValue", { ...props.modelValue, [name]: value });
}

function onSave(): void {
  emit("save");
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-3">
      <div>
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Inställningar
        </h2>
        <p class="text-xs text-navy/60">
          Sparas per användare och gäller för nästa körning.
        </p>
      </div>

      <button
        type="button"
        :disabled="isLoading || isSaving"
        class="btn-ghost px-3 py-2"
        @click="onSave"
      >
        <span
          v-if="isSaving"
          class="inline-block w-3 h-3 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
        />
        <span v-else>Spara</span>
      </button>
    </div>

    <div
      v-if="isLoading"
      class="flex items-center gap-2 text-sm text-navy/70"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Laddar inställningar...</span>
    </div>

    <div
      v-else
      class="grid gap-4"
    >
      <UiActionFieldRenderer
        v-for="field in schema"
        :key="field.name"
        :field="field"
        :id-base="fieldIdBase"
        :model-value="valueForField(field)"
        @update:model-value="updateField(field.name, $event)"
      />
    </div>

    <div
      v-if="successMessage"
      class="p-3 border border-success bg-success/10 shadow-brutal-sm text-sm text-success"
    >
      {{ successMessage }}
    </div>

    <div
      v-if="errorMessage"
      class="p-3 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>
  </div>
</template>
