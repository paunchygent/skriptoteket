<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import type { components } from "../../api/openapi";
import UiActionFieldRenderer from "./UiActionFieldRenderer.vue";

type UiFormAction = components["schemas"]["UiFormAction"];
type UiActionField = NonNullable<UiFormAction["fields"]>[number];

type FieldValue = string | boolean | string[];

const props = withDefaults(
  defineProps<{
    action: UiFormAction;
    idBase: string;
    disabled?: boolean;
  }>(),
  { disabled: false },
);

const emit = defineEmits<{
  submit: [payload: { actionId: string; input: Record<string, components["schemas"]["JsonValue"]> }];
}>();

const errorMessage = ref<string | null>(null);

const textValues = reactive<Record<string, string>>({});
const booleanValues = reactive<Record<string, boolean>>({});
const multiEnumValues = reactive<Record<string, string[]>>({});

const fields = computed(() => props.action.fields ?? []);

function ensureDefaults(): void {
  for (const field of fields.value) {
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
  if (field.kind === "boolean") {
    return booleanValues[field.name] ?? false;
  }
  if (field.kind === "multi_enum") {
    return multiEnumValues[field.name] ?? [];
  }
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

function buildInput(): Record<string, components["schemas"]["JsonValue"]> {
  const input: Record<string, components["schemas"]["JsonValue"]> = {};

  for (const field of fields.value) {
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

function onSubmit(): void {
  if (props.disabled) return;
  errorMessage.value = null;

  try {
    const input = buildInput();
    emit("submit", { actionId: props.action.action_id, input });
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : "Ogiltig indata.";
  }
}

onMounted(() => {
  ensureDefaults();
});

watch(fields, () => {
  ensureDefaults();
});
</script>

<template>
  <form
    class="p-4 border border-navy bg-white shadow-brutal-sm space-y-4"
    @submit.prevent="onSubmit"
  >
    <div
      v-if="errorMessage"
      class="p-3 border border-error text-error bg-canvas text-sm"
    >
      {{ errorMessage }}
    </div>

    <UiActionFieldRenderer
      v-for="field in fields"
      :key="field.name"
      :field="field"
      :id-base="`${idBase}-a-${action.action_id}`"
      :model-value="modelValueFor(field)"
      @update:model-value="(value) => updateModelValue(field, value)"
    />

    <button
      type="submit"
      class="px-4 py-2 border border-navy bg-burgundy text-canvas shadow-brutal font-semibold uppercase tracking-wide btn-secondary-hover transition-colors disabled:opacity-50"
      :disabled="disabled"
    >
      {{ action.label }}
    </button>
  </form>
</template>
