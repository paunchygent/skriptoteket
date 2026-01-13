<template>
  <div
    ref="container"
    class="h-full w-full"
  />
</template>

<script setup lang="ts">
import { defaultKeymap } from "@codemirror/commands";
import { defaultHighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { Compartment, EditorState, type Extension } from "@codemirror/state";
import {
  drawSelection,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  highlightSpecialChars,
  keymap,
  lineNumbers,
} from "@codemirror/view";
import { MergeView } from "@codemirror/merge";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    beforeText: string;
    afterText: string;
    language?: Extension | null;
    tabSize?: number;
    collapseUnchanged?: boolean;
  }>(),
  {
    language: null,
    tabSize: 4,
    collapseUnchanged: true,
  },
);

const container = ref<HTMLDivElement | null>(null);

let mergeView: MergeView | null = null;

const languageCompartment = new Compartment();
const tabSizeCompartment = new Compartment();

const editorTheme = EditorView.theme(
  {
    "&": {
      fontSize: "13px",
      fontFamily: "var(--huleedu-font-mono)",
      height: "100%",
    },
    ".cm-content": {
      padding: "8px 0",
    },
    ".cm-scroller": {
      height: "100%",
    },
  },
  { dark: false },
);

function baseExtensions(): Extension[] {
  return [
    lineNumbers(),
    highlightActiveLineGutter(),
    highlightSpecialChars(),
    drawSelection(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    highlightActiveLine(),
    keymap.of([...defaultKeymap]),
    tabSizeCompartment.of(EditorState.tabSize.of(props.tabSize)),
    languageCompartment.of(props.language ?? []),
    editorTheme,
    EditorView.editable.of(false),
    EditorState.readOnly.of(true),
  ];
}

function replaceDoc(view: EditorView, next: string): void {
  const current = view.state.doc.toString();
  if (current === next) return;
  view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: next } });
}

function mountMergeView(parent: HTMLElement): void {
  mergeView = new MergeView({
    parent,
    a: {
      doc: props.beforeText,
      extensions: baseExtensions(),
    },
    b: {
      doc: props.afterText,
      extensions: baseExtensions(),
    },
    gutter: true,
    highlightChanges: true,
    collapseUnchanged: props.collapseUnchanged ? { margin: 3, minSize: 4 } : undefined,
  });

  mergeView.dom.style.height = "100%";
  mergeView.dom.style.width = "100%";
  mergeView.dom.style.overflow = "auto";
  mergeView.a.dom.style.height = "100%";
  mergeView.b.dom.style.height = "100%";
}

function destroyMergeView(): void {
  mergeView?.destroy();
  mergeView = null;
}

onMounted(() => {
  const parent = container.value;
  if (!parent) {
    throw new Error("Merge diff mount element is missing");
  }
  mountMergeView(parent);
});

watch(
  () => props.beforeText,
  (value) => {
    if (!mergeView) return;
    replaceDoc(mergeView.a, value);
  },
);

watch(
  () => props.afterText,
  (value) => {
    if (!mergeView) return;
    replaceDoc(mergeView.b, value);
  },
);

watch(
  () => props.language,
  (language) => {
    if (!mergeView) return;
    const extension = language ?? [];
    mergeView.a.dispatch({ effects: languageCompartment.reconfigure(extension) });
    mergeView.b.dispatch({ effects: languageCompartment.reconfigure(extension) });
  },
);

watch(
  () => props.tabSize,
  (tabSize) => {
    if (!mergeView) return;
    mergeView.a.dispatch({ effects: tabSizeCompartment.reconfigure(EditorState.tabSize.of(tabSize)) });
    mergeView.b.dispatch({ effects: tabSizeCompartment.reconfigure(EditorState.tabSize.of(tabSize)) });
  },
);

watch(
  () => props.collapseUnchanged,
  (collapseUnchanged) => {
    mergeView?.reconfigure({
      collapseUnchanged: collapseUnchanged ? { margin: 3, minSize: 4 } : undefined,
    });
  },
);

onBeforeUnmount(() => {
  destroyMergeView();
});
</script>

<style scoped>
:global(.cm-mergeView) {
  height: 100%;
}

:global(.cm-mergeView .cm-editor) {
  height: 100%;
}
</style>
