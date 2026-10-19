<script setup lang="ts">
/**
 * Exam workspace rich-text editor.
 *
 * Domain purpose:
 *   The one editor every exam text field uses (question text, part
 *   instruction, exam instruction, and — compact — a choice option, a
 *   Kategorisera entry or an ordering step). One stored body is one TipTap
 *   document, so it edits like a word processor: a selection across
 *   paragraphs deletes with Backspace, Backspace at a paragraph start merges,
 *   Enter starts a paragraph and Shift+Enter breaks the line. Gaps and
 *   pictures are inline atoms: a highlighted range deletes them without
 *   confirmation, and the first Backspace after one selects it.
 *
 *   Every document change emits the mapped body at once. `structural` is true
 *   when the gaps or pictures changed, when a toolbar click changed the marks
 *   or heading, or when the transaction itself is a discrete edit (a mark or
 *   heading changed from the keyboard, or text deleted across paragraphs;
 *   `examWorkspaceRichTextEditKind`), so the owner records one undo step for
 *   it; typing, Enter and paste coalesce. Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z and
 *   Ctrl+Y are the workspace's Ångra and Gör om (`examWorkspaceHistoryKeys`),
 *   never an editor-local undo. The component is a `RichTextTarget`: focusing
 *   it makes it the surface the shared formatting toolbar acts on. The target
 *   also carries `makeGap`: the selection, or the word at the caret, becomes
 *   one new gap in one `createGap` event, never an `update`. A click inside a
 *   word shows a small floating "Lucka" button above that word ("Gör till
 *   lucka" tooltip and accessible name) while a next gap id is available;
 *   one click on it converts the word. The button
 *   teleports to the document body and sits fixed at viewport coordinates, so
 *   the editor's clipping never cuts it; later transactions keep it while the
 *   document is unchanged and the caret stays inside the word.
 *
 * Relationships:
 *   - `examWorkspaceRichTextSchema` builds the editor's extensions;
 *     `examWorkspaceRichTextDocument` maps the body to and from them.
 *   - `examWorkspaceRichTextEditKind` classifies a transaction as a discrete edit.
 *   - `examWorkspaceRichTextTarget` registers the surface for the toolbar.
 *   - `examWorkspaceGapWord` resolves the caret word the floating button converts.
 *   - `examWorkspaceHistoryKeys` receives the undo and redo shortcuts.
 *   - Atom and heading styles are global in `examWorkspace.css`.
 */

import { EditorContent, useEditor } from "@tiptap/vue-3";
import { NodeSelection, TextSelection } from "@tiptap/pm/state";
import type { EditorState, Transaction } from "@tiptap/pm/state";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import type { Ref } from "vue";
import { TextCursorInput } from "lucide-vue-next";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import { BODY_MARKS } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { useExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import {
  bodyFromEditor,
  editorContentFrom,
  placedAssetIds,
  placedGapIds,
} from "./examWorkspaceRichTextDocument";
import { isDiscreteEdit } from "./examWorkspaceRichTextEditKind";
import {
  ATOM_STATE_KEY,
  EXAM_GAP_NODE,
  EXAM_PICTURE_NODE,
  examRichTextExtensions,
} from "./examWorkspaceRichTextSchema";
import type { ExamGapState } from "./examWorkspaceRichTextSchema";
import { wordRangeAt } from "./examWorkspaceGapWord";
import { useRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel, RichTextTarget } from "./examWorkspaceRichTextTarget";
import { ANCHORED_EDGE_PX, ANCHORED_GAP_PX } from "./useExamWorkspaceAnchoredPosition";

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    body: NativeExamBodyParagraph[];
    /** Accessible name of the editing surface. */
    label: string;
    /** `data-test` of the editing surface. */
    testId: string;
    disabled?: boolean;
    /** "field" flows inside the surrounding `.xw-rich__body`; "compact" has its own input-like border. */
    variant?: "field" | "compact";
    invalid?: boolean;
    describedBy?: string;
    /** Border colour of the compact variant. */
    borderClass?: string;
    /** How each gap is drawn; a gap with no entry reads "Lucka" and counts as empty. */
    gapStates?: Record<string, ExamGapState>;
    /** Protected URL per picture id. */
    assetUrls?: Record<string, string>;
    /** Whether a click on a gap, or Enter on a selected gap, opens it. */
    gapsInteractive?: boolean;
    /** The id the next created gap takes; the floating gap button needs a string. */
    nextGapId?: string | null;
  }>(),
  {
    disabled: false,
    variant: "field",
    invalid: false,
    describedBy: undefined,
    borderClass: "border-navy/35",
    gapStates: undefined,
    assetUrls: undefined,
    gapsInteractive: false,
    nextGapId: undefined,
  },
);

const emit = defineEmits<{
  update: [body: NativeExamBodyParagraph[], structural: boolean];
  /** One new gap replaced text at the caret: the owner adds the gap record. */
  createGap: [body: NativeExamBodyParagraph[], gapId: string, seed: string];
  activateGap: [gapId: string, element: HTMLElement];
  focus: [];
}>();

const UNKNOWN_GAP: ExamGapState = { label: "Lucka", accessibleLabel: "Lucka", empty: true };

const registry = useRichTextTargetRegistry();
const historyKeys = useExamWorkspaceHistoryKeys();

/** Gap ids and picture ids in body order, as one comparable key. */
function atomKey(body: readonly NativeExamBodyParagraph[]): string {
  return JSON.stringify([placedGapIds(body), placedAssetIds(body)]);
}

let emitted = JSON.stringify(props.body);
let knownAtoms = atomKey(props.body);
/** True while a toolbar click runs, so its one change is one undo step. */
let toolbarEdit = false;
/** Set while a gap replacement dispatches, so its one change emits `createGap`. */
let gapCreation: { gapId: string; seed: string } | null = null;

const marks: Ref<BodyMark[]> = ref([]);

/** The floating "Lucka" button ("Gör till lucka" tooltip and accessible name): the stored word it converts and where it sits. */
type MakeGapButton = { gapId: string; from: number; to: number; seed: string; left: number; top: number };
const makeGapButton: Ref<MakeGapButton | null> = ref(null);
const makeGapButtonElement: Ref<HTMLButtonElement | null> = ref(null);

/** Gap creation is available only while gaps are interactive and the editor is enabled. */
function canMakeGap(): boolean {
  return props.gapsInteractive && !props.disabled;
}

/** Hide the floating button on any viewport move while it is shown. */
function onMakeGapViewportChange(): void {
  hideMakeGap();
}

let makeGapListenersActive = false;

/** Watch viewport moves only while the button is shown. */
function addMakeGapListeners(): void {
  if (makeGapListenersActive) {
    return;
  }
  makeGapListenersActive = true;
  window.addEventListener("scroll", onMakeGapViewportChange, { capture: true, passive: true });
  window.addEventListener("resize", onMakeGapViewportChange);
}

function removeMakeGapListeners(): void {
  if (!makeGapListenersActive) {
    return;
  }
  makeGapListenersActive = false;
  window.removeEventListener("scroll", onMakeGapViewportChange, true);
  window.removeEventListener("resize", onMakeGapViewportChange);
}

function hideMakeGap(): void {
  makeGapButton.value = null;
  removeMakeGapListeners();
}

/**
 * Hide the floating button when a transaction leaves its stored word: any
 * document change, a non-empty selection, or a caret outside the word. The
 * click's own caret placement and meta-only redraws keep it.
 */
function maybeHideMakeGapButton(transaction: Transaction): void {
  const current = makeGapButton.value;
  if (current === null) {
    return;
  }
  if (transaction.docChanged) {
    hideMakeGap();
    return;
  }
  const { selection } = transaction;
  if (!selection.empty || selection.head < current.from || selection.head > current.to) {
    hideMakeGap();
  }
}

/** Place the floating button above its word, or below it when there is no room above. */
function placeMakeGapButton(): void {
  const current = makeGapButton.value;
  const view = editor.value?.view;
  if (current === null || !view) {
    return;
  }
  let coords: { left: number; top: number; bottom: number };
  try {
    coords = view.coordsAtPos(current.from);
  } catch {
    hideMakeGap();
    return;
  }
  const height = makeGapButtonElement.value?.offsetHeight ?? 0;
  const width = makeGapButtonElement.value?.offsetWidth ?? 0;
  let top = coords.top - height - ANCHORED_GAP_PX;
  if (top < ANCHORED_EDGE_PX) {
    top = coords.bottom + ANCHORED_GAP_PX;
  }
  const maxLeft = window.innerWidth - width - ANCHORED_EDGE_PX;
  const left =
    maxLeft < ANCHORED_EDGE_PX
      ? ANCHORED_EDGE_PX
      : Math.min(Math.max(coords.left, ANCHORED_EDGE_PX), maxLeft);
  if (makeGapButton.value !== current) {
    return;
  }
  makeGapButton.value = { ...current, left, top };
}

function showMakeGapButton(gapId: string, from: number, to: number, seed: string): void {
  makeGapButton.value = { gapId, from, to, seed, left: 0, top: 0 };
  addMakeGapListeners();
  void nextTick(placeMakeGapButton);
}

/** The word at a document position, or null when the position is not inside a word. */
function wordAtPos(state: EditorState, pos: number): { from: number; to: number } | null {
  const doc = state.doc;
  if (pos < 0 || pos > doc.content.size) {
    return null;
  }
  const resolved = doc.resolve(pos);
  const parent = resolved.parent;
  if (!parent.isTextblock) {
    return null;
  }
  const blockStart = resolved.pos - resolved.parentOffset;
  let found: { from: number; to: number } | null = null;
  parent.forEach((child, childOffset) => {
    if (found !== null || !child.isText || child.text === undefined) {
      return;
    }
    if (pos < blockStart + childOffset || pos > blockStart + childOffset + child.text.length) {
      return;
    }
    const range = wordRangeAt(child.text, pos - (blockStart + childOffset));
    if (range !== null) {
      found = { from: blockStart + childOffset + range.from, to: blockStart + childOffset + range.to };
    }
  });
  return found;
}

/** The word at an empty text selection, as document positions, or null. */
function wordAtCaret(state: EditorState): { from: number; to: number } | null {
  const { selection } = state;
  if (!(selection instanceof TextSelection) || !selection.empty) {
    return null;
  }
  const $cursor = selection.$cursor;
  if (!$cursor) {
    return null;
  }
  const parent = $cursor.parent;
  if (!parent.isTextblock) {
    return null;
  }
  const offset = $cursor.parentOffset;
  let found: { from: number; to: number } | null = null;
  parent.forEach((child, childOffset) => {
    if (found !== null || !child.isText || child.text === undefined) {
      return;
    }
    if (offset < childOffset || offset > childOffset + child.text.length) {
      return;
    }
    const range = wordRangeAt(child.text, offset - childOffset);
    if (range !== null) {
      found = { from: $cursor.pos - offset + range.from, to: $cursor.pos - offset + range.to };
    }
  });
  return found;
}

/**
 * Replace `from`..`to` with one new gap and emit one `createGap`, never an
 * `update`. The caller owns the range: the selection for the toolbar command,
 * the stored click word for the floating button.
 */
function replaceRangeWithGap(gapId: string, from: number, to: number, seed: string): void {
  const current = editor.value;
  if (!current || !canMakeGap()) {
    return;
  }
  const gapType = current.state.schema.nodes[EXAM_GAP_NODE];
  if (!gapType) {
    return;
  }
  const replaced = current.state.tr.replaceWith(from, to, gapType.create({ gapId }));
  const withGapSelected = replaced.setSelection(NodeSelection.create(replaced.doc, from));
  hideMakeGap();
  gapCreation = { gapId, seed };
  try {
    current.view.dispatch(withGapSelected);
  } finally {
    gapCreation = null;
  }
}

/**
 * Turn the selection, or the word at the caret, into one new gap with
 * `gapId`, or insert an empty gap at the caret. The replacement dispatches
 * as one transaction and emits one `createGap`, never an `update`.
 */
function makeGap(gapId: string): void {
  const current = editor.value;
  if (!current || !canMakeGap()) {
    return;
  }
  const { state } = current;
  const { selection } = state;
  if (selection instanceof TextSelection && !selection.empty) {
    const { $from, $to } = selection;
    if (!$from.sameParent($to) || !$from.parent.isTextblock) {
      return;
    }
    let hasAtom = false;
    state.doc.nodesBetween($from.pos, $to.pos, (node) => {
      if (node.type.name === EXAM_GAP_NODE || node.type.name === EXAM_PICTURE_NODE) {
        hasAtom = true;
        return false;
      }
      return true;
    });
    if (hasAtom) {
      return;
    }
    const selected = state.doc.textBetween($from.pos, $to.pos, "\n", " ");
    if (selected.trim() === "") {
      return;
    }
    replaceRangeWithGap(gapId, $from.pos, $to.pos, selected.trim());
  } else if (selection instanceof TextSelection && selection.empty) {
    const word = wordAtCaret(state);
    if (word !== null) {
      replaceRangeWithGap(gapId, word.from, word.to, state.doc.textBetween(word.from, word.to, "\n", " "));
    } else {
      replaceRangeWithGap(gapId, selection.from, selection.from, "");
    }
  }
}

/** Convert the stored click word; the caret may have moved inside it since. */
function confirmMakeGap(): void {
  const stored = makeGapButton.value;
  hideMakeGap();
  if (stored === null) {
    return;
  }
  replaceRangeWithGap(stored.gapId, stored.from, stored.to, stored.seed);
}

const editor = useEditor({
  content: editorContentFrom(props.body),
  editable: !props.disabled,
  extensions: examRichTextExtensions({
    gapState: (gapId) => props.gapStates?.[gapId] ?? UNKNOWN_GAP,
    pictureUrl: (assetId) => props.assetUrls?.[assetId],
    onUndo: () => historyKeys?.undo(),
    onRedo: () => historyKeys?.redo(),
  }),
  editorProps: {
    attributes: surfaceAttributes(),
    handleClickOn: (view, _pos, node, nodePos) => {
      if (node.type.name !== EXAM_GAP_NODE || !props.gapsInteractive || props.disabled) {
        return false;
      }
      const element = view.nodeDOM(nodePos);
      if (!(element instanceof HTMLElement)) {
        return false;
      }
      emit("activateGap", String(node.attrs.gapId), element);
      return true;
    },
    handleClick: (view, pos, event) => {
      hideMakeGap();
      if (!canMakeGap() || typeof props.nextGapId !== "string") {
        return false;
      }
      if (event instanceof MouseEvent && event.button !== 0) {
        return false;
      }
      const word = wordAtPos(view.state, pos);
      if (word === null) {
        return false;
      }
      showMakeGapButton(
        props.nextGapId,
        word.from,
        word.to,
        view.state.doc.textBetween(word.from, word.to, "\n", " "),
      );
      return false;
    },
    handleKeyDown: (view, event) => {
      if (event.key === "Escape" && makeGapButton.value !== null) {
        hideMakeGap();
        return false;
      }
      const { selection } = view.state;
      if (
        (event.key !== "Enter" && event.key !== " ") ||
        !(selection instanceof NodeSelection) ||
        selection.node.type.name !== EXAM_GAP_NODE ||
        !props.gapsInteractive ||
        props.disabled
      ) {
        return false;
      }
      const element = view.nodeDOM(selection.from);
      if (!(element instanceof HTMLElement)) {
        return false;
      }
      emit("activateGap", String(selection.node.attrs.gapId), element);
      return true;
    },
  },
  onUpdate: ({ editor: current, transaction }) => {
    maybeHideMakeGapButton(transaction);
    if (props.disabled) {
      return;
    }
    const body = bodyFromEditor(current.getJSON());
    const atoms = atomKey(body);
    const creation = gapCreation;
    const structural = toolbarEdit || atoms !== knownAtoms || isDiscreteEdit(transaction);
    emitted = JSON.stringify(body);
    knownAtoms = atoms;
    if (creation !== null) {
      emit("createGap", body, creation.gapId, creation.seed);
      return;
    }
    emit("update", body, structural);
  },
  onTransaction: ({ editor: current, transaction }) => {
    maybeHideMakeGapButton(transaction);
    marks.value = BODY_MARKS.filter((mark) => current.isActive(mark));
  },
  onFocus: () => {
    registry.activate(target);
    emit("focus");
  },
  onBlur: () => {
    hideMakeGap();
  },
});

function surfaceAttributes(): Record<string, string> {
  return {
    class: "xw-richtext__surface",
    role: "textbox",
    "aria-multiline": "true",
    "aria-label": props.label,
    "data-test": props.testId,
    ...(props.invalid ? { "aria-invalid": "true" } : {}),
    ...(props.describedBy ? { "aria-describedby": props.describedBy } : {}),
  };
}

function currentHeadingLevel(): RichTextHeadingLevel | null {
  const current = editor.value;
  if (!current) {
    return null;
  }
  for (const level of [1, 2, 3] as const) {
    if (current.isActive("heading", { level })) {
      return level;
    }
  }
  return null;
}

/** Run one toolbar change; it is one undo step however small. */
function asToolbarEdit(run: () => void): void {
  toolbarEdit = true;
  try {
    run();
  } finally {
    toolbarEdit = false;
  }
}

const target: RichTextTarget = {
  marks,
  headingLevel: currentHeadingLevel,
  toggleMark: (mark) => {
    asToolbarEdit(() => editor.value?.chain().focus().toggleMark(mark).run());
  },
  toggleHeading: (level) => {
    asToolbarEdit(() => {
      const chain = editor.value?.chain().focus();
      if (currentHeadingLevel() === level) {
        chain?.setParagraph().run();
      } else {
        chain?.setHeading({ level }).run();
      }
    });
  },
  makeGap: (gapId) => {
    makeGap(gapId);
  },
  // ProseMirror keeps its own selection while the toolbar has focus.
  release: () => undefined,
};

onBeforeUnmount(() => {
  registry.deactivate(target);
  removeMakeGapListeners();
});

watch(
  () => props.body,
  (body) => {
    const json = JSON.stringify(body);
    if (json === emitted) {
      return;
    }
    emitted = json;
    knownAtoms = atomKey(body);
    editor.value?.commands.setContent(editorContentFrom(body), { emitUpdate: false });
  },
);

watch(
  () => props.disabled,
  (disabled) => {
    editor.value?.setEditable(!disabled, false);
    if (disabled) {
      hideMakeGap();
    }
  },
);

watch(
  () => props.nextGapId,
  (nextGapId) => {
    if (typeof nextGapId !== "string") {
      hideMakeGap();
    }
  },
);

/** Redraw gap labels and pictures in place, without a document change. */
function redrawAtoms(): void {
  const view = editor.value?.view;
  view?.dispatch(view.state.tr.setMeta(ATOM_STATE_KEY, true));
}
watch(() => [props.gapStates, props.assetUrls], redrawAtoms, { deep: true });

function setSurfaceAttribute(name: string, value: string | undefined): void {
  const surface = editor.value?.view.dom;
  if (value === undefined) {
    surface?.removeAttribute(name);
  } else {
    surface?.setAttribute(name, value);
  }
}
watch(
  [editor, () => props.label, () => props.invalid, () => props.describedBy, () => props.testId],
  () => {
    setSurfaceAttribute("aria-label", props.label);
    setSurfaceAttribute("aria-invalid", props.invalid ? "true" : undefined);
    setSurfaceAttribute("aria-describedby", props.describedBy);
    setSurfaceAttribute("data-test", props.testId);
  },
);

const wrapperClass = computed(() =>
  props.variant === "compact"
    ? [
        "xw-richtext--compact border bg-panel px-2 py-1.5 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-action/40",
        props.invalid ? "border-error" : props.borderClass,
      ]
    : [],
);

defineExpose({
  focus(): void {
    editor.value?.commands.focus("end");
  },
});
</script>

<template>
  <div class="contents">
    <EditorContent
      :editor="editor"
      v-bind="$attrs"
      class="xw-richtext"
      :class="wrapperClass"
      :data-disabled="disabled ? 'true' : undefined"
    />
    <Teleport to="body">
      <button
        v-if="makeGapButton !== null"
        ref="makeGapButtonElement"
        type="button"
        class="fixed z-30 inline-flex items-center gap-1 border border-navy/60 bg-panel px-2 py-1 text-xs text-navy shadow"
        :style="{ left: `${makeGapButton.left}px`, top: `${makeGapButton.top}px` }"
        aria-label="Gör till lucka"
        title="Gör till lucka"
        data-test="exam-workspace-make-gap"
        @mousedown.prevent
        @click="confirmMakeGap"
      >
        <TextCursorInput
          :size="14"
          aria-hidden="true"
        />
        Lucka
      </button>
    </Teleport>
  </div>
</template>
