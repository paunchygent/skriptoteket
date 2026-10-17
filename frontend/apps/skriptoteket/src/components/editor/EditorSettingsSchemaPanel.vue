<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { UiDenseActionButton, UiDenseSpinner } from "../ui";
import { computed, defineAsyncComponent, ref } from "vue";
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

const tooltipNonce = Math.random().toString(36).slice(2, 10);
const settingsSchemaHelpTooltipId = `tool-settings-schema-help-${tooltipNonce}`;

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
      isInline ? 'p-3 space-y-3' : 'border border-navy/20 bg-panel p-3 space-y-3',
    ]"
  >
    <div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
      <div class="relative group min-w-0">
        <span
          class="block truncate text-xs font-semibold uppercase tracking-wide text-navy/70"
          tabindex="0"
          :aria-describedby="settingsSchemaHelpTooltipId"
        >
          Inst&auml;llningar
        </span>
        <div
          :id="settingsSchemaHelpTooltipId"
          class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy/30 bg-modal shadow-md text-navy px-3 py-2 text-[11px] opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
          role="tooltip"
        >
          <p class="text-[11px] text-navy/80">
            Valfritt. Ange en JSON-array av f&auml;lt (samma typer som UI Actions: string, text,
            integer, number, boolean, enum, multi_enum).
          </p>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2">
        <UiDenseActionButton
          v-if="!isInline"
          :label="isCollapsed ? 'Visa' : 'Dölj'"
          :expanded="!isCollapsed"
          @click="isCollapsed = !isCollapsed"
        />
        <UiDenseActionButton
          label="formatera"
          :disabled="props.isReadOnly"
          @click="handlePrettifySettings"
        />
        <UiDenseActionButton
          label="förval"
          class="w-[110px]"
          :disabled="props.isReadOnly"
          @click="handleInsertSettingsExample"
        />
      </div>
    </div>

    <div
      v-show="contentVisible"
      class="space-y-3"
    >
      <div
        class="h-[240px] border border-navy/20 bg-canvas overflow-hidden"
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
              <UiDenseSpinner :size="16" />
              <span>Laddar JSON-redigerare...</span>
            </div>
          </template>
        </Suspense>
      </div>

      <p
        v-if="props.settingsSchemaError"
        class="text-xs font-semibold text-critical"
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
