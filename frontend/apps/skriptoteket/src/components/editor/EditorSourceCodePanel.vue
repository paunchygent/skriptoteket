<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { UiDenseSpinner } from "../ui";
import type { Extension } from "@codemirror/state";
import type { EditorView } from "@codemirror/view";
import { computed, defineAsyncComponent, ref, watch } from "vue";

import {
  ENTRY_FILE_NAME,
  bundleFileLanguage,
  sortedBundleFileNames,
  type BundleFiles,
} from "../../composables/editor/bundleFiles";
import { useSkriptoteketIntelligenceExtensions } from "../../composables/editor/useSkriptoteketIntelligenceExtensions";
import { useAiAccess } from "../../composables/useAiAccess";
import { aiDailyLimitNote, aiDailyLimitReached } from "../../composables/aiDailyLimit";

const CodeMirrorEditor = defineAsyncComponent(() => import("./CodeMirrorEditor.vue"));

type EditorSourceCodePanelProps = {
  entrypoint: string;
  sourceCode: string;
  isReadOnly: boolean;
  bundleFiles: BundleFiles;
};

const props = defineProps<EditorSourceCodePanelProps>();

const emit = defineEmits<{
  (event: "update:sourceCode", value: string): void;
  (event: "update:bundleFiles", value: BundleFiles): void;
  (event: "editorViewReady", value: EditorView | null): void;
}>();

const { canUseAi } = useAiAccess();

const entrypointName = computed(() => props.entrypoint);
const ghostTextEnabled = computed(
  () => !props.isReadOnly && canUseAi.value && !aiDailyLimitReached.value,
);
const ghostTextAutoTrigger = computed(() => true);
const ghostTextDebounceMs = computed(() => 1500);

const { extensions: intelligenceExtensions } = useSkriptoteketIntelligenceExtensions({
  entrypointName,
  ghostText: {
    enabled: ghostTextEnabled,
    autoTrigger: ghostTextAutoTrigger,
    debounceMs: ghostTextDebounceMs,
  },
});

const bundleFileNames = computed(() => sortedBundleFileNames(props.bundleFiles));
const showsBundleTabs = computed(() => bundleFileNames.value.length > 0);

// null selects the entrypoint source; any other value selects that bundle file.
const activeFile = ref<string | null>(null);

watch(bundleFileNames, (names) => {
  if (activeFile.value !== null && !names.includes(activeFile.value)) {
    activeFile.value = null;
  }
});

const activeBundleLanguage = computed<Extension | null>(() => {
  const name = activeFile.value;
  if (name === null) return null;
  switch (bundleFileLanguage(name)) {
    case "json":
      return json();
    case "text":
      return [];
    default:
      return null;
  }
});

function selectEntrypointFile(): void {
  activeFile.value = null;
}

function selectBundleFile(name: string): void {
  activeFile.value = name;
}

function updateActiveBundleFile(value: string): void {
  const name = activeFile.value;
  if (name === null) return;
  emit("update:bundleFiles", { ...props.bundleFiles, [name]: value });
}
</script>

<template>
  <div class="flex flex-col min-h-0 h-full">
    <div
      v-if="showsBundleTabs"
      class="mb-2 flex flex-wrap items-center gap-1 border border-navy/30 bg-canvas p-1"
      role="tablist"
      aria-label="Verktygets filer"
    >
      <button
        type="button"
        role="tab"
        :aria-selected="activeFile === null"
        class="px-2 py-1 text-[10px] font-semibold tracking-[var(--huleedu-tracking-label)] leading-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy/40"
        :class="activeFile === null ? 'bg-navy text-canvas' : 'text-navy/70 hover:text-navy'"
        @click="selectEntrypointFile"
      >
        {{ ENTRY_FILE_NAME }}
      </button>
      <button
        v-for="name in bundleFileNames"
        :key="name"
        type="button"
        role="tab"
        :aria-selected="activeFile === name"
        class="px-2 py-1 text-[10px] font-semibold tracking-[var(--huleedu-tracking-label)] leading-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy/40"
        :class="activeFile === name ? 'bg-navy text-canvas' : 'text-navy/70 hover:text-navy'"
        @click="selectBundleFile(name)"
      >
        {{ name }}
      </button>
    </div>

    <div class="relative flex-1 min-h-0 panel-inset-canvas overflow-hidden">
      <Suspense>
        <template #default>
          <div class="h-full w-full">
            <CodeMirrorEditor
              v-show="activeFile === null"
              :model-value="props.sourceCode"
              :extensions="intelligenceExtensions"
              :read-only="props.isReadOnly"
              @view-ready="emit('editorViewReady', $event)"
              @update:model-value="emit('update:sourceCode', $event)"
            />
            <CodeMirrorEditor
              v-if="activeFile !== null"
              :key="activeFile"
              :model-value="props.bundleFiles[activeFile]"
              :read-only="props.isReadOnly"
              :language="activeBundleLanguage"
              @update:model-value="updateActiveBundleFile"
            />
          </div>
        </template>
        <template #fallback>
          <div class="h-full w-full flex items-center justify-center gap-3 text-sm text-navy/70">
            <UiDenseSpinner :size="16" />
            <span>Laddar kodredigerare...</span>
          </div>
        </template>
      </Suspense>
      <p
        v-if="canUseAi && aiDailyLimitNote"
        class="pointer-events-none absolute bottom-2 right-3 z-10 max-w-[calc(100%-1.5rem)] border border-[var(--huleedu-panel-border)] bg-canvas px-2 py-1 text-[10px] text-navy/60"
        role="status"
        data-test="editor-ai-limit-note"
      >
        {{ aiDailyLimitNote }}
      </p>
    </div>
  </div>
</template>
