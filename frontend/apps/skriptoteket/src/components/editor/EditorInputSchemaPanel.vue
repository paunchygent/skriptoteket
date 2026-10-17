<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { denseMenuItemClass, UiDenseActionButton, UiDenseSpinner } from "../ui";
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from "vue";
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

const isCollapsed = ref(false);
const isInline = computed(() => props.variant === "inline");
const contentVisible = computed(() => (isInline.value ? true : !isCollapsed.value));

const tooltipNonce = Math.random().toString(36).slice(2, 10);
const inputSchemaHelpTooltipId = `tool-input-schema-help-${tooltipNonce}`;

const presetMenuRef = ref<HTMLElement | null>(null);
const isPresetMenuOpen = ref(false);

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

function handleApplyPreset(presetId: string): void {
  closePresetMenu();
  if (!confirmSchemaReplace(props.inputSchemaText)) {
    return;
  }
  emit("update:inputSchemaText", buildInputSchemaSnippetText(presetId));
}

function togglePresetMenu(): void {
  isPresetMenuOpen.value = !isPresetMenuOpen.value;
}

function closePresetMenu(): void {
  isPresetMenuOpen.value = false;
}

function handleDocumentClick(event: MouseEvent): void {
  if (!isPresetMenuOpen.value) return;

  const target = event.target as Node | null;
  if (!target) return;

  if (presetMenuRef.value && !presetMenuRef.value.contains(target)) {
    closePresetMenu();
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== "Escape") {
    return;
  }
  if (isPresetMenuOpen.value) {
    event.preventDefault();
    event.stopPropagation();
    closePresetMenu();
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleKeydown);
});
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
          :aria-describedby="inputSchemaHelpTooltipId"
        >
          Indata
        </span>
        <div
          :id="inputSchemaHelpTooltipId"
          class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy/30 bg-modal shadow-md text-navy px-3 py-2 text-[11px] opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
          role="tooltip"
        >
          <p class="text-[11px] text-navy/80">
            Valfritt. Ange en JSON-array av f&auml;lt som visas innan k&ouml;rning (string, text,
            integer, number, boolean, enum, file). V1: max 1 file-f&auml;lt och file-f&auml;lt
            kr&auml;ver min/max.
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
          @click="handlePrettifyInput"
        />

        <div
          ref="presetMenuRef"
          class="relative"
        >
          <UiDenseActionButton
            label="förval"
            class="w-[110px]"
            :disabled="props.isReadOnly"
            :expanded="isPresetMenuOpen"
            has-popup="menu"
            @click="togglePresetMenu"
          >
            <template #trailing>▾</template>
          </UiDenseActionButton>
          <div
            v-if="isPresetMenuOpen"
            class="absolute right-0 top-full mt-2 min-w-full border border-navy/30 bg-modal shadow-md z-[var(--huleedu-z-tooltip)]"
            role="menu"
          >
            <div class="py-1 divide-y divide-navy/20">
              <button
                v-for="preset in inputSchemaPresets"
                :key="preset.id"
                type="button"
                role="menuitem"
                :class="denseMenuItemClass()"
                @click="handleApplyPreset(preset.id)"
              >
                {{ preset.label }}
              </button>
            </div>
          </div>
        </div>
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
              <UiDenseSpinner :size="16" />
              <span>Laddar JSON-redigerare...</span>
            </div>
          </template>
        </Suspense>
      </div>

      <p
        v-if="props.inputSchemaError"
        class="text-xs font-semibold text-critical"
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
