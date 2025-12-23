<script setup lang="ts">
import { computed, onMounted, reactive, watch } from "vue";

import type { components } from "../../api/openapi";
import UiActionFieldRenderer from "../ui-actions/UiActionFieldRenderer.vue";

type UiFormAction = components["schemas"]["UiFormAction"];
type UiActionField = NonNullable<UiFormAction["fields"]>[number];
type FieldValue = string | boolean | string[];

const props = withDefaults(
  defineProps<{
    actions: UiFormAction[];
    idBase: string;
    disabled?: boolean;
    errorMessage?: string | null;
  }>(),
  { disabled: false, errorMessage: null },
);

const emit = defineEmits<{
  submit: [payload: { actionId: string; input: Record<string, components["schemas"]["JsonValue"]> }];
}>();

const textValues = reactive<Record<string, string>>({});
const booleanValues = reactive<Record<string, boolean>>({});
const multiEnumValues = reactive<Record<string, string[]>>({});

const allFields = computed(() => {
  const fields: UiActionField[] = [];
  for (const action of props.actions) {
    if (action.fields) {
      fields.push(...action.fields);
    }
  }
  return fields;
});

function ensureDefaults(): void {
  for (const field of allFields.value) {
    if (field.kind === "boolean") {
      if (booleanValues[field.name] === undefined) {
        booleanValues[field.name] = false;
      }
      continue;
    }
    if (field.kind === "multi_enum") {
      if (multiEnumValues[field.name] === undefined) {
        multiEnumValues[field.name] = [];
      }
      continue;
    }
    if (textValues[field.name] === undefined) {
      textValues[field.name] = "";
    }
  }
}

function modelValueFor(field: UiActionField): FieldValue {
  if (field.kind === "boolean") return booleanValues[field.name] ?? false;
  if (field.kind === "multi_enum") return multiEnumValues[field.name] ?? [];
  return textValues[field.name] ?? "";
}

function updateModelValue(field: UiActionField, value: FieldValue): void {
  if (field.kind === "boolean") {
    booleanValues[field.name] = typeof value === "boolean" ? value : Boolean(value);
    return;
  }
  if (field.kind === "multi_enum") {
    multiEnumValues[field.name] = Array.isArray(value) ? value : [];
    return;
  }
  textValues[field.name] = typeof value === "string" ? value : String(value);
}

function buildInput(action: UiFormAction): Record<string, components["schemas"]["JsonValue"]> {
  const input: Record<string, components["schemas"]["JsonValue"]> = {};
  const fields = action.fields ?? [];

  for (const field of fields) {
    if (field.kind === "boolean") {
      input[field.name] = booleanValues[field.name] ?? false;
      continue;
    }
    if (field.kind === "multi_enum") {
      input[field.name] = multiEnumValues[field.name] ?? [];
      continue;
    }

    const raw = textValues[field.name] ?? "";
    const rawStr = String(raw);

    if (field.kind === "integer") {
      const str = rawStr.trim();
      if (!str) continue;
      const parsed = Number.parseInt(str, 10);
      if (Number.isNaN(parsed)) throw new Error(`Ogiltigt heltal: ${field.label}`);
      input[field.name] = parsed;
      continue;
    }
    if (field.kind === "number") {
      const str = rawStr.trim();
      if (!str) continue;
      const parsed = Number.parseFloat(str);
      if (Number.isNaN(parsed)) throw new Error(`Ogiltigt tal: ${field.label}`);
      input[field.name] = parsed;
      continue;
    }
    if (field.kind === "enum") {
      if (!rawStr) continue;
      input[field.name] = rawStr;
      continue;
    }
    input[field.name] = rawStr;
  }

  return input;
}

function onSubmit(action: UiFormAction): void {
  if (props.disabled) return;
  try {
    const input = buildInput(action);
    emit("submit", { actionId: action.action_id, input });
  } catch {
    // Error handling done by parent
  }
}

onMounted(() => ensureDefaults());
watch(allFields, () => ensureDefaults());
</script>

<template>
  <div
    v-if="actions.length > 0"
    class="space-y-4"
  >
    <div
      v-if="errorMessage"
      class="text-sm text-error"
    >
      {{ errorMessage }}
    </div>

    <div
      v-if="allFields.length > 0"
      class="space-y-3"
    >
      <UiActionFieldRenderer
        v-for="field in allFields"
        :key="field.name"
        :field="field"
        :id-base="`${idBase}-field`"
        :model-value="modelValueFor(field)"
        @update:model-value="(value) => updateModelValue(field, value)"
      />
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="action in actions"
        :key="action.action_id"
        type="button"
        class="px-4 py-2 text-xs font-bold uppercase tracking-widest border border-navy shadow-brutal-sm transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
        :class="action === actions[0]
          ? 'bg-burgundy text-canvas btn-secondary-hover'
          : 'bg-canvas text-navy hover:bg-white'"
        :disabled="disabled"
        @click="onSubmit(action)"
      >
        {{ action.label }}
      </button>
    </div>
  </div>
</template>
