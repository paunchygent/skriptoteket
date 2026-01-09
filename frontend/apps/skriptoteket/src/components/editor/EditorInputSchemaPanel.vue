<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { computed, defineAsyncComponent, ref, withDefaults } from "vue";
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
  variant?: "standalone" | "inline";
  inputSchemaText: string;
  inputSchemaError: string | null;
  schemaIssues: SchemaValidationIssue[];
  isReadOnly: boolean;
};

const props = withDefaults(defineProps<EditorInputSchemaPanelProps>(), {
  variant: "standalone",
});

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
const presetTooltipLines = computed(() => {
  const lines: string[] = [];
  if (inputPresetDescription.value) {
    lines.push(inputPresetDescription.value);
  }
  lines.push(...inputPresetGuidance.value);
  return lines;
});
const presetTooltipId = "tool-input-schema-preset-help";
const isCollapsed = ref(false);
const isInline = computed(() => props.variant === "inline");
const contentVisible = computed(() => (isInline.value ? true : !isCollapsed.value));

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
  <div
    :class="[
      isInline ? 'p-3 space-y-3' : 'border border-navy/20 bg-white shadow-brutal-sm p-3 space-y-3',
    ]"
  >
    <div class="space-y-2">
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Indata
          </span>
          <div class="relative group">
            <button
              type="button"
              class="inline-flex h-3.5 w-3.5 items-center justify-center text-[9px] font-semibold leading-none text-navy/50 hover:text-navy self-center -translate-y-[3px]"
              aria-label="Visa hjälp"
            >
              ?
            </button>
            <div
              class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy/30 bg-white text-navy px-3 py-2 text-[11px] opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
              role="tooltip"
            >
              <p class="text-[11px] text-navy/80">
                Valfritt. Ange en JSON-array av f&auml;lt som visas innan k&ouml;rning (string,
                text, integer, number, boolean, enum, file). V1: max 1 file-f&auml;lt och
                file-f&auml;lt kr&auml;ver min/max.
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
        <div class="flex items-center gap-2 min-w-0">
          <label
            for="tool-input-schema-preset"
            class="text-[10px] font-semibold uppercase tracking-wide text-navy/60"
          >
            F&ouml;rval
          </label>
          <select
            id="tool-input-schema-preset"
            v-model="selectedInputPresetId"
            :aria-describedby="presetTooltipLines.length ? presetTooltipId : undefined"
            class="h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none"
          >
            <option
              v-for="preset in inputSchemaPresets"
              :key="preset.id"
              :value="preset.id"
            >
              {{ preset.label }}
            </option>
          </select>
          <div
            v-if="presetTooltipLines.length"
            class="relative group"
          >
            <button
              type="button"
              class="inline-flex h-3.5 w-3.5 items-center justify-center text-[9px] font-semibold leading-none text-navy/50 hover:text-navy self-center -translate-y-[3px]"
              aria-label="Visa hjälp"
            >
              ?
            </button>
            <div
              :id="presetTooltipId"
              class="absolute left-0 top-full mt-2 w-[min(280px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy/30 bg-white text-navy px-3 py-2 text-[11px] opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
              role="tooltip"
            >
              <div class="space-y-1">
                <p
                  v-for="(line, index) in presetTooltipLines"
                  :key="index"
                  class="text-[11px] text-navy/80"
                >
                  {{ line }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
            :disabled="props.isReadOnly"
            @click="handlePrettifyInput"
          >
            Formatera
          </button>
          <button
            type="button"
            class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
            :disabled="props.isReadOnly"
            @click="handleInsertInputExample"
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
  </div>
</template>
