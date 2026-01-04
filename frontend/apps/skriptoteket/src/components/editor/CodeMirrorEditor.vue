<template>
  <div
    ref="container"
    class="h-full w-full"
  />
</template>

<script setup lang="ts">
import {
  autocompletion,
  closeBrackets,
  closeBracketsKeymap,
  completionKeymap,
} from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { Compartment, EditorState, type Extension } from "@codemirror/state";
import {
  bracketMatching,
  defaultHighlightStyle,
  foldGutter,
  foldKeymap,
  indentOnInput,
  syntaxHighlighting,
} from "@codemirror/language";
import { python } from "@codemirror/lang-python";
import { highlightSelectionMatches, searchKeymap } from "@codemirror/search";
import {
  crosshairCursor,
  drawSelection,
  dropCursor,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  highlightSpecialChars,
  keymap,
  lineNumbers,
  rectangularSelection,
} from "@codemirror/view";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    extensions?: Extension[];
    readOnly?: boolean;
    language?: Extension | null;
    tabSize?: number;
  }>(),
  {
    extensions: () => [],
    readOnly: false,
    language: null,
    tabSize: 4,
  },
);
const emit = defineEmits<{
  "update:modelValue": [value: string];
  viewReady: [view: EditorView | null];
}>();

const container = ref<HTMLDivElement | null>(null);

let view: EditorView | null = null;
let suppressEmit = false;

const externalExtensions = new Compartment();
const readOnlyExtension = new Compartment();
const languageExtension = new Compartment();
const tabSizeExtension = new Compartment();

const editorLayoutTheme = EditorView.theme(
  {
    "&": {
      height: "100%",
      fontSize: "14px",
    },
    ".cm-scroller": {
      overflow: "auto",
    },
  },
  { dark: false },
);

onMounted(() => {
  const parent = container.value;
  if (!parent) {
    throw new Error("CodeMirror mount element is missing");
  }

  const updateListener = EditorView.updateListener.of((update) => {
    if (!update.docChanged) return;
    if (suppressEmit) return;
    emit("update:modelValue", update.state.doc.toString());
  });

  view = new EditorView({
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        highlightSpecialChars(),
        history(),
        foldGutter(),
        drawSelection(),
        dropCursor(),
        EditorState.allowMultipleSelections.of(true),
        indentOnInput(),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        bracketMatching(),
        closeBrackets(),
        autocompletion(),
        rectangularSelection(),
        crosshairCursor(),
        highlightActiveLine(),
        highlightSelectionMatches(),
        keymap.of([
          indentWithTab,
          ...closeBracketsKeymap,
          ...defaultKeymap,
          ...searchKeymap,
          ...historyKeymap,
          ...foldKeymap,
          ...completionKeymap,
        ]),
        languageExtension.of(props.language ?? python()),
        tabSizeExtension.of(EditorState.tabSize.of(props.tabSize)),
        editorLayoutTheme,
        externalExtensions.of(props.extensions),
        readOnlyExtension.of([
          EditorView.editable.of(!props.readOnly),
          EditorState.readOnly.of(props.readOnly),
        ]),
        updateListener,
      ],
    }),
    parent,
  });
  emit("viewReady", view);
});

watch(
  () => props.modelValue,
  (value) => {
    if (!view) return;

    const current = view.state.doc.toString();
    if (value === current) return;

    suppressEmit = true;
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: value },
    });
    suppressEmit = false;
  },
);

watch(
  () => props.extensions,
  (extensions) => {
    if (!view) return;
    view.dispatch({
      effects: externalExtensions.reconfigure(extensions),
    });
  },
);

watch(
  () => props.language,
  (language) => {
    if (!view) return;
    view.dispatch({
      effects: languageExtension.reconfigure(language ?? python()),
    });
  },
);

watch(
  () => props.tabSize,
  (tabSize) => {
    if (!view) return;
    view.dispatch({
      effects: tabSizeExtension.reconfigure(EditorState.tabSize.of(tabSize)),
    });
  },
);

watch(
  () => props.readOnly,
  (readOnly) => {
    if (!view) return;
    view.dispatch({
      effects: readOnlyExtension.reconfigure([
        EditorView.editable.of(!readOnly),
        EditorState.readOnly.of(readOnly),
      ]),
    });
  },
);

onBeforeUnmount(() => {
  emit("viewReady", null);
  view?.destroy();
  view = null;
});
</script>
