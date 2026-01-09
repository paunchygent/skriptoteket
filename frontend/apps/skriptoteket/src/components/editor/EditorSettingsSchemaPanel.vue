<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { computed, defineAsyncComponent, ref, withDefaults } from "vue";
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
  variant?: "standalone" | "inline";
  settingsSchemaText: string;
  settingsSchemaError: string | null;
  schemaIssues: SchemaValidationIssue[];
  isReadOnly: boolean;
};

const props = withDefaults(defineProps<EditorSettingsSchemaPanelProps>(), {
  variant: "standalone",
});

const emit = defineEmits<{
  (event: "update:settingsSchemaText", value: string): void;
}>();

const jsonLanguage = json();

const settingsSchemaExtensions = schemaJsonEditorExtensions({
  label: "Inställningsschemat",
  emptyValue: null,
});
const isCollapsed = ref(false);
const isInline = computed(() => props.variant === "inline");
const contentVisible = computed(() => (isInline.value ? true : !isCollapsed.value));

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
  <div
    :class="[
      isInline ? 'p-3 space-y-3' : 'border border-navy/20 bg-white shadow-brutal-sm p-3 space-y-3',
    ]"
  >
    <div class="space-y-2">
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Inst&auml;llningar
          </span>
          <div class="relative group">
            <button
              type="button"
              class="inline-flex h-3.5 w-3.5 items-center justify-center text-[9px] font-semibold leading-none text-navy/50 hover:text-navy self-center -translate-y-[3px]"
              aria-label="Info om inställningsschema"
            >
              ?
            </button>
            <div
              class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy/30 bg-white text-navy px-3 py-2 text-[11px] opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
              role="tooltip"
            >
              <p class="text-[11px] text-navy/80">
                Valfritt. Ange en JSON-array av f&auml;lt (samma typer som UI Actions: string,
                text, integer, number, boolean, enum, multi_enum).
              </p>
            </div>
          </div>
        </div>
        <button
          v-if="!isInline"
          type="button"
          class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
          :aria-expanded="!isCollapsed"
          @click="isCollapsed = !isCollapsed"
        >
          {{ isCollapsed ? "Visa" : "D&ouml;lj" }}
        </button>
      </div>

      <div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
        <div
          class="min-h-[24px]"
          aria-hidden="true"
        />
        <div class="flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
            :disabled="props.isReadOnly"
            @click="handlePrettifySettings"
          >
            Formatera
          </button>
          <button
            type="button"
            class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
            :disabled="props.isReadOnly"
            @click="handleInsertSettingsExample"
          >
            Infoga exempel
          </button>
        </div>
      </div>
    </div>

    <div
      v-show="contentVisible"
      class="space-y-3"
    >
      <div
        :class="[
          'h-[240px] border border-navy bg-canvas overflow-hidden',
          isInline ? '' : 'shadow-brutal-sm',
        ]"
      >
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
  </div>
</template>
