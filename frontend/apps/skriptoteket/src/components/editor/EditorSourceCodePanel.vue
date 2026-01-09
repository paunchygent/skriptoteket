<script setup lang="ts">
import type { EditorView } from "@codemirror/view";
import { computed, defineAsyncComponent } from "vue";

import { useSkriptoteketIntelligenceExtensions } from "../../composables/editor/useSkriptoteketIntelligenceExtensions";

const CodeMirrorEditor = defineAsyncComponent(() => import("./CodeMirrorEditor.vue"));

type EditorSourceCodePanelProps = {
  entrypoint: string;
  sourceCode: string;
  isReadOnly: boolean;
};

const props = defineProps<EditorSourceCodePanelProps>();

const emit = defineEmits<{
  (event: "update:sourceCode", value: string): void;
  (event: "editorViewReady", value: EditorView | null): void;
}>();

const entrypointName = computed(() => props.entrypoint);
const ghostTextEnabled = computed(() => !props.isReadOnly);
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
</script>

<template>
  <div class="flex flex-col min-h-0 h-full">
    <div class="flex-1 min-h-0 border border-navy bg-canvas shadow-brutal-sm overflow-hidden">
      <Suspense>
        <template #default>
          <CodeMirrorEditor
            :model-value="props.sourceCode"
            :extensions="intelligenceExtensions"
            :read-only="props.isReadOnly"
            @view-ready="emit('editorViewReady', $event)"
            @update:model-value="emit('update:sourceCode', $event)"
          />
        </template>
        <template #fallback>
          <div class="h-full w-full flex items-center justify-center gap-3 text-sm text-navy/70">
            <span
              class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
            />
            <span>Laddar kodredigerare...</span>
          </div>
        </template>
      </Suspense>
    </div>
  </div>
</template>
