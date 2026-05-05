<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import type { components } from "../../api/openapi";
import type { FileRefInfo } from "../../composables/tools/fileRefHelpers";
import { filterFileRefsBySources } from "../../composables/tools/fileRefHelpers";
import UiActionFieldRenderer from "./UiActionFieldRenderer.vue";

type UiFormAction = components["schemas"]["UiFormAction"];
type UiActionField = NonNullable<UiFormAction["fields"]>[number];

type FieldValue = string | boolean | string[];

const props = withDefaults(
  defineProps<{
    action: UiFormAction;
    idBase: string;
    disabled?: boolean;
    availableFileRefs?: FileRefInfo[];
  }>(),
  { disabled: false, availableFileRefs: () => [] },
);

const emit = defineEmits<{
  submit: [
    payload: {
      actionId: string;
      input: Record<string, components["schemas"]["JsonValue"]>;
      fileRefsByField?: Record<string, string[]>;
    },
  ];
}>();

const errorMessage = ref<string | null>(null);

const textValues = reactive<Record<string, string>>({});
const booleanValues = reactive<Record<string, boolean>>({});
const multiEnumValues = reactive<Record<string, string[]>>({});
const fileRefValues = reactive<Record<string, string[]>>({});
const fileRefDirty = reactive<Record<string, boolean>>({});

const fields = computed(() => props.action.fields ?? []);
const isString = (value: unknown): value is string => typeof value === "string";

function ensureDefaults(): void {
  for (const field of fields.value) {
    const prefill = props.action.prefill ?? {};
    if (prefill[field.name] !== undefined) {
      const value = prefill[field.name];

      if (field.kind === "boolean") {
        if (booleanValues[field.name] === undefined && typeof value === "boolean") {
          booleanValues[field.name] = value;
        }
      } else if (field.kind === "multi_enum") {
        if (
          multiEnumValues[field.name] === undefined &&
          Array.isArray(value) &&
          value.every((item) => typeof item === "string")
        ) {
          multiEnumValues[field.name] = value;
        }
      } else if (field.kind === "file_ref") {
        const validRefs = Array.isArray(value) ? value.filter(isString) : [];
        if (fileRefDirty[field.name] === undefined) {
          fileRefDirty[field.name] = false;
        }
        if (!fileRefDirty[field.name] && validRefs.length > 0) {
          const unique = Array.from(new Set(validRefs));
          const allowedSources = field.sources?.length ? field.sources : null;
          const availableSet = new Set(
            filterFileRefsBySources(props.availableFileRefs, allowedSources).map((ref) => ref.ref),
          );
          fileRefValues[field.name] = unique.filter((ref) => availableSet.has(ref));
        }
      } else if (textValues[field.name] === undefined) {
        if (typeof value === "string") {
          textValues[field.name] = value;
        } else if (
          (field.kind === "integer" || field.kind === "number") &&
          typeof value === "number" &&
          Number.isFinite(value)
        ) {
          textValues[field.name] = String(value);
        }
      }
    }

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

    if (field.kind === "file_ref") {
      if (fileRefValues[field.name] === undefined) {
        fileRefValues[field.name] = [];
      }
      if (fileRefDirty[field.name] === undefined) {
        fileRefDirty[field.name] = false;
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
  if (field.kind === "file_ref") {
    return fileRefValues[field.name] ?? [];
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
  if (field.kind === "file_ref") {
    fileRefValues[field.name] = Array.isArray(value) ? value : [];
    fileRefDirty[field.name] = true;
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
    if (field.kind === "file_ref") {
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

function buildFileRefsByField(): Record<string, string[]> {
  const refsByField: Record<string, string[]> = {};
  for (const field of fields.value) {
    if (field.kind !== "file_ref") continue;
    const refs = fileRefValues[field.name] ?? [];
    if (refs.length > 0) {
      refsByField[field.name] = refs;
    }
  }
  return refsByField;
}

const fileRefErrors = computed<Record<string, string | null>>(() => {
  const errors: Record<string, string | null> = {};
  for (const field of fields.value) {
    if (field.kind !== "file_ref") continue;
    const selected = fileRefValues[field.name] ?? [];
    const allowedSources = field.sources?.length ? field.sources : null;
    const availableSet = new Set(
      filterFileRefsBySources(props.availableFileRefs, allowedSources).map((ref) => ref.ref),
    );
    const prefillValue = (props.action.prefill ?? {})[field.name];
    const prefillRefs = Array.isArray(prefillValue) ? prefillValue.filter(isString) : [];
    const missing = prefillRefs.filter((ref) => !availableSet.has(ref));
    if (!fileRefDirty[field.name] && missing.length > 0) {
      errors[field.name] = "En förvald fil saknas. Välj en ny fil.";
      continue;
    }
    if (selected.length < field.min) {
      errors[field.name] = field.min === 1 ? "Välj minst en fil." : `Välj minst ${field.min} filer.`;
      continue;
    }
    if (selected.length > field.max) {
      errors[field.name] = field.max === 1 ? "Du kan välja max 1 fil." : `Du kan välja max ${field.max} filer.`;
      continue;
    }
    errors[field.name] = null;
  }
  return errors;
});

const hasFileRefErrors = computed(() => {
  return Object.values(fileRefErrors.value).some((value) => value !== null);
});

function onSubmit(): void {
  if (props.disabled || hasFileRefErrors.value) return;
  errorMessage.value = null;

  try {
    const input = buildInput();
    const fileRefsByField = buildFileRefsByField();
    emit("submit", { actionId: props.action.action_id, input, fileRefsByField });
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
watch(
  () => props.availableFileRefs,
  () => ensureDefaults(),
  { deep: true },
);
</script>

<template>
  <form
    class="p-4 border border-navy bg-panel shadow-brutal-sm space-y-4"
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
      :available-file-refs="availableFileRefs"
      :file-ref-errors="fileRefErrors"
      @update:model-value="(value) => updateModelValue(field, value)"
    />

    <button
      type="submit"
      class="btn-cta"
      :disabled="disabled || hasFileRefErrors"
    >
      {{ action.label }}
    </button>
  </form>
</template>
