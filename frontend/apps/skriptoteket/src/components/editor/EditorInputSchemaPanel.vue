<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { computed, defineAsyncComponent, ref } from "vue";
import type { components } from "../../api/openapi";

import {
  buildInputSchemaSnippetText,
  inputSchemaPresets,
  prettifySchemaJsonText,
  schemaJsonEditorExtensions,
  schemaTextHasContent,
} from "../../composables/editor/schemaJsonEditor";
import EditorSchemaIssuesList from "./EditorSchemaIssuesList.vue";

const CodeMirrorEditor = defineAsyncComponent(() => import("./CodeMirrorEditor.vue"));

type SchemaValidationIssue = components["schemas"]["SchemaValidationIssue"];

type EditorInputSchemaPanelProps = {
  inputSchemaText: string;
  inputSchemaError: string | null;
  schemaIssues: SchemaValidationIssue[];
  isReadOnly: boolean;
};

const props = defineProps<EditorInputSchemaPanelProps>();

const emit = defineEmits<{
  (event: "update:inputSchemaText", value: string): void;
}>();

const jsonLanguage = json();

const inputSchemaExtensions = schemaJsonEditorExtensions({
  label: "Indata-schemat",
  emptyValue: [],
});

const selectedInputPresetId = ref(inputSchemaPresets[0]?.id ?? "basic-text");
const selectedInputPreset = computed(() => {
  return inputSchemaPresets.find((preset) => preset.id === selectedInputPresetId.value) ??
    inputSchemaPresets[0];
});
const inputPresetDescription = computed(() => selectedInputPreset.value?.description ?? "");
const inputPresetGuidance = computed(() => selectedInputPreset.value?.guidance ?? []);

function confirmSchemaReplace(currentText: string): boolean {
  if (!schemaTextHasContent(currentText)) {
    return true;
  }
  return window.confirm("Indata-schemat är inte tomt. Detta ersätter innehållet. Fortsätt?");
}

function handlePrettifyInput(): void {
  const result = prettifySchemaJsonText(props.inputSchemaText, "Indata-schemat", []);
  if (result.text === null) return;
  emit("update:inputSchemaText", result.text);
}

function handleInsertInputExample(): void {
  if (!confirmSchemaReplace(props.inputSchemaText)) {
    return;
  }
  emit("update:inputSchemaText", buildInputSchemaSnippetText(selectedInputPresetId.value));
}
</script>

<template>
  <div class="border-t border-navy/20 pt-4 space-y-3">
    <div class="space-y-1">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Indata (input_schema)
      </h2>
      <p class="text-sm text-navy/60">
        Valfritt. Ange en JSON-array av fält som visas innan körning (string, text, integer,
        number, boolean, enum, file). V1: max 1 file-fält och file-fält kräver min/max.
      </p>
    </div>

    <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div class="min-w-[220px] space-y-1">
        <label
          for="tool-input-schema-preset"
          class="text-xs font-semibold uppercase tracking-wide text-navy/70"
        >
          Preset
        </label>
        <select
          id="tool-input-schema-preset"
          v-model="selectedInputPresetId"
          class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
        >
          <option
            v-for="preset in inputSchemaPresets"
            :key="preset.id"
            :value="preset.id"
          >
            {{ preset.label }}
          </option>
        </select>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          :disabled="props.isReadOnly"
          @click="handlePrettifyInput"
        >
          Formatera
        </button>
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          :disabled="props.isReadOnly"
          @click="handleInsertInputExample"
        >
          Infoga exempel
        </button>
      </div>
    </div>

    <div
      v-if="inputPresetDescription || inputPresetGuidance.length"
      class="space-y-1 text-xs text-navy/60"
    >
      <p v-if="inputPresetDescription">
        {{ inputPresetDescription }}
      </p>
      <p
        v-for="(line, index) in inputPresetGuidance"
        :key="index"
      >
        {{ line }}
      </p>
    </div>

    <label
      for="tool-input-schema"
      class="text-xs font-semibold uppercase tracking-wide text-navy/70"
    >
      Schema (JSON)
    </label>
    <div class="h-[240px] border border-navy bg-canvas shadow-brutal-sm overflow-hidden">
      <Suspense>
        <template #default>
          <CodeMirrorEditor
            id="tool-input-schema"
            :model-value="props.inputSchemaText"
            :extensions="inputSchemaExtensions"
            :language="jsonLanguage"
            :tab-size="2"
            :read-only="props.isReadOnly"
            @update:model-value="emit('update:inputSchemaText', $event)"
          />
        </template>
        <template #fallback>
          <div class="h-full w-full flex items-center justify-center gap-3 text-sm text-navy/70">
            <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
            <span>Laddar JSON-redigerare...</span>
          </div>
        </template>
      </Suspense>
    </div>

    <p
      v-if="props.inputSchemaError"
      class="text-xs font-semibold text-burgundy"
    >
      {{ props.inputSchemaError }}
    </p>
    <EditorSchemaIssuesList
      v-else
      :issues="props.schemaIssues"
    />
  </div>
</template>
