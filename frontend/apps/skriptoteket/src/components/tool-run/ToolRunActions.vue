<script setup lang="ts">
import { computed, onMounted, reactive, watch } from "vue";

import type { components } from "../../api/openapi";
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
  }>(),
  { disabled: false, density: "default", errorMessage: null },
);

const emit = defineEmits<{
  submit: [payload: { actionId: string; input: Record<string, components["schemas"]["JsonValue"]> }];
  "update:errorMessage": [value: string | null];
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

const isCompact = computed(() => props.density === "compact");

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
    :class="[isCompact ? 'border border-navy/20 bg-white shadow-brutal-sm' : 'space-y-4']"
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
          :disabled="disabled"
          @click="onSubmit(action)"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
  </div>
</template>
