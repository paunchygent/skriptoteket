<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { defineAsyncComponent } from "vue";
import type { components } from "../../api/openapi";

import {
  buildSettingsSchemaSnippetText,
  prettifySchemaJsonText,
  schemaJsonEditorExtensions,
  schemaTextHasContent,
} from "../../composables/editor/schemaJsonEditor";
import EditorSchemaIssuesList from "./EditorSchemaIssuesList.vue";

const CodeMirrorEditor = defineAsyncComponent(() => import("./CodeMirrorEditor.vue"));

type SchemaValidationIssue = components["schemas"]["SchemaValidationIssue"];

type EditorSettingsSchemaPanelProps = {
  settingsSchemaText: string;
  settingsSchemaError: string | null;
  schemaIssues: SchemaValidationIssue[];
  isReadOnly: boolean;
};

const props = defineProps<EditorSettingsSchemaPanelProps>();

const emit = defineEmits<{
  (event: "update:settingsSchemaText", value: string): void;
}>();

const jsonLanguage = json();

const settingsSchemaExtensions = schemaJsonEditorExtensions({
  label: "Inställningsschemat",
  emptyValue: null,
});

function confirmSchemaReplace(currentText: string): boolean {
  if (!schemaTextHasContent(currentText)) {
    return true;
  }
  return window.confirm("Inställningsschemat är inte tomt. Detta ersätter innehållet. Fortsätt?");
}

function handlePrettifySettings(): void {
  const result = prettifySchemaJsonText(props.settingsSchemaText, "Inställningsschemat", null);
  if (result.text === null) return;
  emit("update:settingsSchemaText", result.text);
}

function handleInsertSettingsExample(): void {
  if (!confirmSchemaReplace(props.settingsSchemaText)) {
    return;
  }
  emit("update:settingsSchemaText", buildSettingsSchemaSnippetText());
}
</script>

<template>
  <div class="border-t border-navy/20 pt-4 space-y-3">
    <div class="space-y-1">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Inställningar (schema)
      </h2>
      <p class="text-sm text-navy/60">
        Valfritt. Ange en JSON-array av fält (samma typer som UI Actions: string, text,
        integer, number, boolean, enum, multi_enum).
      </p>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <button
        type="button"
        class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
        :disabled="props.isReadOnly"
        @click="handlePrettifySettings"
      >
        Formatera
      </button>
      <button
        type="button"
        class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
        :disabled="props.isReadOnly"
        @click="handleInsertSettingsExample"
      >
        Infoga exempel
      </button>
    </div>

    <label
      for="tool-settings-schema"
      class="text-xs font-semibold uppercase tracking-wide text-navy/70"
    >
      Schema (JSON)
    </label>
    <div class="h-[240px] border border-navy bg-canvas shadow-brutal-sm overflow-hidden">
      <Suspense>
        <template #default>
          <CodeMirrorEditor
            id="tool-settings-schema"
            :model-value="props.settingsSchemaText"
            :extensions="settingsSchemaExtensions"
            :language="jsonLanguage"
            :tab-size="2"
            :read-only="props.isReadOnly"
            @update:model-value="emit('update:settingsSchemaText', $event)"
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
      v-if="props.settingsSchemaError"
      class="text-xs font-semibold text-burgundy"
    >
      {{ props.settingsSchemaError }}
    </p>
    <EditorSchemaIssuesList
      v-else
      :issues="props.schemaIssues"
    />
  </div>
</template>
