<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import UiActionFieldRenderer from "../ui-actions/UiActionFieldRenderer.vue";
import SystemMessage from "../ui/SystemMessage.vue";

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
  isSaveDisabled?: boolean;
  errorMessage: string | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: SettingsFormValues];
  "update:errorMessage": [value: string | null];
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
        :disabled="isLoading || isSaving || props.isSaveDisabled"
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

    <SystemMessage
      :model-value="errorMessage"
      variant="error"
      @update:model-value="emit('update:errorMessage', $event)"
    />
  </div>
</template>
