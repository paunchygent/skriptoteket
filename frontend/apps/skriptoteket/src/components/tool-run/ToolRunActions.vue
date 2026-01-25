<script setup lang="ts">
import { computed, onMounted, reactive, watch } from "vue";

import type { components } from "../../api/openapi";
import type { FileRefInfo } from "../../composables/tools/fileRefHelpers";
import { filterFileRefsBySources } from "../../composables/tools/fileRefHelpers";
import UiActionFieldRenderer from "../ui-actions/UiActionFieldRenderer.vue";
import SystemMessage from "../ui/SystemMessage.vue";

type UiFormAction = components["schemas"]["UiFormAction"];
type UiActionField = NonNullable<UiFormAction["fields"]>[number];
type FieldValue = string | boolean | string[];

const props = withDefaults(
  defineProps<{
    actions: UiFormAction[];
    idBase: string;
    disabled?: boolean;
    density?: "default" | "compact";
    errorMessage?: string | null;
    availableFileRefs?: FileRefInfo[];
  }>(),
  { disabled: false, density: "default", errorMessage: null, availableFileRefs: () => [] },
);

const emit = defineEmits<{
  submit: [
    payload: {
      actionId: string;
      input: Record<string, components["schemas"]["JsonValue"]>;
      fileRefsByField?: Record<string, string[]>;
    },
  ];
  "update:errorMessage": [value: string | null];
}>();

const textValues = reactive<Record<string, string>>({});
const booleanValues = reactive<Record<string, boolean>>({});
const multiEnumValues = reactive<Record<string, string[]>>({});
const fileRefValues = reactive<Record<string, string[]>>({});
const fileRefDirty = reactive<Record<string, boolean>>({});
const isString = (value: unknown): value is string => typeof value === "string";

const allFields = computed(() => {
  const fields: UiActionField[] = [];
  for (const action of props.actions) {
    if (action.fields) {
      fields.push(...action.fields);
    }
  }
  return fields;
});

const isCompact = computed(() => props.density === "compact");

function ensureDefaults(): void {
  const prefillByField = (name: string): components["schemas"]["JsonValue"] | undefined => {
    for (const action of props.actions) {
      const prefill = action.prefill ?? {};
      if (prefill[name] !== undefined) return prefill[name];
    }
    return undefined;
  };

  for (const field of allFields.value) {
    const value = prefillByField(field.name);

    if (value !== undefined) {
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
  if (field.kind === "boolean") return booleanValues[field.name] ?? false;
  if (field.kind === "multi_enum") return multiEnumValues[field.name] ?? [];
  if (field.kind === "file_ref") return fileRefValues[field.name] ?? [];
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

function buildFileRefsByField(action: UiFormAction): Record<string, string[]> {
  const refsByField: Record<string, string[]> = {};
  const fields = action.fields ?? [];
  for (const field of fields) {
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
  const prefillByField = (name: string): string[] => {
    for (const action of props.actions) {
      const prefill = action.prefill ?? {};
      const value = prefill[name];
      if (Array.isArray(value)) {
        return value.filter(isString);
      }
    }
    return [];
  };

  for (const field of allFields.value) {
    if (field.kind !== "file_ref") continue;
    const selected = fileRefValues[field.name] ?? [];
    const allowedSources = field.sources?.length ? field.sources : null;
    const availableSet = new Set(
      filterFileRefsBySources(props.availableFileRefs, allowedSources).map((ref) => ref.ref),
    );
    const missing = prefillByField(field.name).filter((ref) => !availableSet.has(ref));
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

function onSubmit(action: UiFormAction): void {
  if (props.disabled || hasFileRefErrors.value) return;
  try {
    const input = buildInput(action);
    const fileRefsByField = buildFileRefsByField(action);
    emit("submit", { actionId: action.action_id, input, fileRefsByField });
  } catch {
    // Error handling done by parent
  }
}

onMounted(() => ensureDefaults());
watch(allFields, () => ensureDefaults());
watch(
  () => props.availableFileRefs,
  () => ensureDefaults(),
  { deep: true },
);
</script>

<template>
  <div
    v-if="actions.length > 0"
    :class="[isCompact ? 'panel-inset' : 'space-y-4']"
  >
    <div
      v-if="isCompact"
      class="border-b border-navy/20 px-3 py-2 flex items-center justify-between gap-3"
    >
      <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
        &Aring;tg&auml;rder
      </span>
      <span class="text-[10px] text-navy/60">
        {{ actions.length }}
      </span>
    </div>

    <div :class="[isCompact ? 'p-3 space-y-3' : 'space-y-4']">
      <SystemMessage
        :model-value="errorMessage"
        variant="error"
        @update:model-value="emit('update:errorMessage', $event)"
      />

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
          :available-file-refs="availableFileRefs"
          :file-ref-errors="fileRefErrors"
          :density="isCompact ? 'compact' : 'default'"
          @update:model-value="(value) => updateModelValue(field, value)"
        />
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          v-for="action in actions"
          :key="action.action_id"
          type="button"
          :class="[
            isCompact
              ? 'btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none'
              : (action === actions[0] ? 'btn-cta' : 'btn-ghost'),
          ]"
          :disabled="disabled || hasFileRefErrors"
          @click="onSubmit(action)"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
  </div>
</template>
