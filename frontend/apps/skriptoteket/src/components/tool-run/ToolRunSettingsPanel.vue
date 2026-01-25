<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import type { FileRefInfo, FileRefSource } from "../../composables/tools/fileRefHelpers";
import { filterFileRefsBySources } from "../../composables/tools/fileRefHelpers";
import UiActionFieldRenderer from "../ui-actions/UiActionFieldRenderer.vue";
import SystemMessage from "../ui/SystemMessage.vue";

type ToolSettingsResponse = components["schemas"]["ToolSettingsResponse"];
type SettingsField = NonNullable<ToolSettingsResponse["settings_schema"]>[number];
type SettingsFieldKind = SettingsField["kind"];

type FieldValue = string | boolean | string[];
type SettingsFormValues = Record<string, FieldValue>;

const props = withDefaults(defineProps<{
  idBase: string;
  schema: SettingsField[];
  modelValue: SettingsFormValues;
  isLoading: boolean;
  isSaving: boolean;
  variant?: "standalone" | "embedded";
  density?: "default" | "compact";
  isSaveDisabled?: boolean;
  errorMessage: string | null;
  availableFileRefs?: FileRefInfo[];
}>(), {
  variant: "standalone",
  density: "default",
  isSaveDisabled: false,
  availableFileRefs: () => [],
});

const emit = defineEmits<{
  "update:modelValue": [value: SettingsFormValues];
  "update:errorMessage": [value: string | null];
  save: [];
}>();

const fieldIdBase = computed(() => `${props.idBase}-settings`);
const isCompact = computed(() => props.variant === "embedded" || props.density === "compact");
const vaultSources: FileRefSource[] = ["vault"];
const vaultFileRefs = computed(() => filterFileRefsBySources(props.availableFileRefs ?? [], vaultSources));

const fileRefErrors = computed<Record<string, string | null>>(() => {
  const errors: Record<string, string | null> = {};
  const availableSet = new Set(vaultFileRefs.value.map((ref) => ref.ref));

  for (const field of props.schema) {
    if (field.kind !== "file_ref") continue;
    const raw = props.modelValue[field.name];
    const selected = Array.isArray(raw) ? raw.filter((item) => typeof item === "string") : [];
    const missing = selected.filter((ref) => !availableSet.has(ref));
    if (missing.length > 0) {
      errors[field.name] = "Vald fil finns inte längre i valvet. Välj en ny fil.";
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

const isSaveDisabled = computed(() => props.isSaveDisabled || hasFileRefErrors.value);

function defaultValueForKind(kind: SettingsFieldKind): FieldValue {
  switch (kind) {
    case "boolean":
      return false;
    case "multi_enum":
      return [];
    case "file_ref":
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
  <div :class="[isCompact ? 'space-y-3' : 'space-y-4']">
    <div
      v-if="props.variant === 'standalone'"
      class="flex items-center justify-between gap-3"
    >
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
        :disabled="isLoading || isSaving || isSaveDisabled"
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
      v-else
      class="flex items-center justify-end gap-2"
    >
      <button
        type="button"
        :disabled="isLoading || isSaving || isSaveDisabled"
        class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
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
      :class="[isCompact ? 'flex items-center gap-2 text-[11px] text-navy/70' : 'flex items-center gap-2 text-sm text-navy/70']"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Laddar inställningar...</span>
    </div>

    <div
      v-else
      :class="[isCompact ? 'grid gap-3' : 'grid gap-4']"
    >
      <UiActionFieldRenderer
        v-for="field in schema"
        :key="field.name"
        :field="field"
        :id-base="fieldIdBase"
        :model-value="valueForField(field)"
        :available-file-refs="vaultFileRefs"
        :file-ref-errors="fileRefErrors"
        :file-ref-sources-override="vaultSources"
        :density="isCompact ? 'compact' : 'default'"
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
