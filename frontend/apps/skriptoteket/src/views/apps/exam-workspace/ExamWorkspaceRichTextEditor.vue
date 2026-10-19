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
 *   word shows a small glyph-only floating button ("Gör till lucka" tooltip
 *   and accessible name only) in the line gap under that word's end, covering
 *   no letters; Tab in the surface moves focus to it while it stays shown,
 *   Enter or Space converts the word, Escape hides it and returns focus to
 *   the surface with the caret where it was, Shift+Tab returns focus to the
 *   surface and keeps it shown, and Tab from it moves focus past the editor
 *   and hides it. While the optional `gapTool` prop is
 *   true, a click on the pointer-hit word or a primary drag selection inside
 *   one paragraph becomes a gap at once through the same replacement, and
 *   the button never shows: a click on a space or punctuation only places
 *   the caret, and a release converts only after a primary press started in
 *   this editor. Escape in the surface reaches the owner as `escape` (after the
 *   button takes its own Escape), so the owner closes a popover first and
 *   the tool second. The button
 *   teleports to the document body and sits fixed at viewport coordinates, so
 *   the editor's clipping never cuts it; later transactions keep it while the
 *   document is unchanged and the caret stays inside the word. A blur whose
 *   focus moves into the button keeps it; any other blur hides it.
 *
 * Relationships:
 *   - `examWorkspaceRichTextSchema` builds the editor's extensions;
 *     `examWorkspaceRichTextDocument` maps the body to and from them.
 *   - `examWorkspaceRichTextEditKind` classifies a transaction as a discrete edit.
 *   - `examWorkspaceRichTextTarget` registers the surface for the toolbar.
 *   - `useExamWorkspaceMakeGap` owns the Lucka command and the floating
 *     button; it resolves words with `examWorkspaceGapWord`.
 *   - `examWorkspaceHistoryKeys` receives the undo and redo shortcuts; the
 *     gap tool shortcut reaches the owner as `toggleGapTool`.
 *   - Atom and heading styles are global in `examWorkspace.css`.
 */

import { EditorContent, useEditor } from "@tiptap/vue-3";
import { NodeSelection } from "@tiptap/pm/state";
import { computed, onBeforeUnmount, ref, watch } from "vue";
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
  examRichTextExtensions,
} from "./examWorkspaceRichTextSchema";
import type { ExamGapState } from "./examWorkspaceRichTextSchema";
import { MAKE_GAP_BUTTON_GLYPH, useExamWorkspaceMakeGap } from "./useExamWorkspaceMakeGap";
import { useRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel, RichTextTarget } from "./examWorkspaceRichTextTarget";

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
    /** While true, a word click or a drag selection becomes a gap at once. */
    gapTool?: boolean;
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
    gapTool: false,
  },
);

const emit = defineEmits<{
  update: [body: NativeExamBodyParagraph[], structural: boolean];
  /** One new gap replaced text at the caret: the owner adds the gap record. */
  createGap: [body: NativeExamBodyParagraph[], gapId: string, seed: string];
  activateGap: [gapId: string, element: HTMLElement];
  /** Ctrl+Alt+G (Cmd+Option+G on macOS) in an editor whose gaps are interactive. */
  toggleGapTool: [];
  /**
   * Escape in the surface, after the floating button takes its own Escape.
   * The owner closes an open gap popover first and the gap tool second.
   */
  escape: [];
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

const marks: Ref<BodyMark[]> = ref([]);

/** Gap creation is available only while gaps are interactive and the editor is enabled. */
function canMakeGap(): boolean {
  return props.gapsInteractive && !props.disabled;
}

const editor = useEditor({
  content: editorContentFrom(props.body),
  editable: !props.disabled,
  extensions: examRichTextExtensions({
    gapState: (gapId) => props.gapStates?.[gapId] ?? UNKNOWN_GAP,
    pictureUrl: (assetId) => props.assetUrls?.[assetId],
    onUndo: () => historyKeys?.undo(),
    onRedo: () => historyKeys?.redo(),
    onToggleGapTool: () => {
      if (!canMakeGap()) {
        return false;
      }
      emit("toggleGapTool");
      return true;
    },
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
      return handleMakeGapClick(view, pos, event);
    },
    handleDOMEvents: {
      mousedown: (_view, event) => {
        handleGapToolMouseDown(event);
        return false;
      },
      mouseup: (_view, event) => {
        handleGapToolMouseUp(event);
        return false;
      },
    },
    handleKeyDown: (view, event) => {
      if (event.key === "Tab" && !event.shiftKey && makeGapButton.value !== null) {
        event.preventDefault();
        // A roving hand-off: Tab in the surface reaches the floating action
        // without moving the caret, and the action stays shown for it.
        focusMakeGapButton();
        return true;
      }
      if (event.key === "Escape" && event.repeat) {
        // A held Escape is one press: repeats emit nothing.
        return false;
      }
      if (event.key === "Escape" && makeGapButton.value !== null) {
        hideMakeGap();
        return false;
      }
      if (event.key === "Escape") {
        emit("escape");
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
    const creation = pendingGapCreation();
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
  onBlur: ({ event }) => {
    const target = event.relatedTarget;
    if (target instanceof HTMLElement && target === makeGapButtonElement.value) {
      return;
    }
    hideMakeGap();
  },
});

const {
  makeGapButton,
  makeGapButtonElement,
  pendingGapCreation,
  makeGap,
  confirmMakeGap,
  handleMakeGapClick,
  handleGapToolMouseDown,
  handleGapToolMouseUp,
  maybeHideMakeGapButton,
  hideMakeGap,
  removeMakeGapListeners,
  focusMakeGapButton,
  handleMakeGapButtonKeyDown,
  handleMakeGapButtonFocusOut,
} = useExamWorkspaceMakeGap({
  editor,
  canMakeGap,
  nextGapId: () => props.nextGapId,
  gapTool: () => props.gapTool,
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

watch(
  () => props.gapTool,
  (gapTool) => {
    if (gapTool) {
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
        class="fixed z-30 inline-flex items-center justify-center text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action/40"
        :style="{ left: `${makeGapButton.left}px`, top: `${makeGapButton.top}px`, width: `${makeGapButton.width}px`, height: `${makeGapButton.height}px` }"
        aria-label="Gör till lucka"
        title="Gör till lucka"
        data-test="exam-workspace-make-gap"
        @mousedown.prevent
        @click="confirmMakeGap"
        @keydown="handleMakeGapButtonKeyDown"
        @focusout="handleMakeGapButtonFocusOut"
      >
        <TextCursorInput
          :size="makeGapButton.height < MAKE_GAP_BUTTON_GLYPH ? makeGapButton.height : MAKE_GAP_BUTTON_GLYPH"
          aria-hidden="true"
        />
      </button>
    </Teleport>
  </div>
</template>
