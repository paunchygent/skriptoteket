/**
 * Exam workspace make-gap command and floating gap button.
 *
 * Domain purpose:
 *   The one place that turns a word into a gap: the shared toolbar's Lucka
 *   command (the selection, or the word at the caret) and the small
 *   glyph-only floating button ("Gör till lucka" tooltip and accessible
 *   name only) right after a clicked word, on that word's own line. Both paths resolve the word with the same whole-textblock
 *   resolver in document positions, replace it with one gap atom in one
 *   transaction, and seed the gap from the replaced document text. While the
 *   gap tool is on, a word click converts at once through the same
 *   replacement and a drag selection converts on mouseup; the button never
 *   shows. A tool click converts only the word the pointer actually hit (a
 *   click on a space or punctuation only places the caret), and a release
 *   converts only after a primary press started in this editor, so a
 *   right-click over a selection never makes a gap. The button
 *   teleports to the document body and sits fixed at viewport coordinates, so
 *   the editor's clipping never cuts it; later transactions keep it while the
 *   document is unchanged and the caret stays inside the word.
 *
 * Relationships:
 *   - Wired in by `ExamWorkspaceRichTextEditor`, which owns the editor, the
 *     button template and the `createGap` emit boundary.
 *   - Resolves words with `examWorkspaceGapWord`.
 *   - Places the button with the shared anchored constants.
 */

import type { Editor } from "@tiptap/core";
import { NodeSelection, TextSelection } from "@tiptap/pm/state";
import type { Transaction } from "@tiptap/pm/state";
import type { EditorView } from "@tiptap/pm/view";
import { nextTick, ref } from "vue";
import type { Ref } from "vue";

import { EXAM_GAP_NODE, EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";
import { wordRangeAtDocCharacter, wordRangeAtDocPosition } from "./examWorkspaceGapWord";
import { ANCHORED_EDGE_PX, ANCHORED_GAP_PX } from "./useExamWorkspaceAnchoredPosition";

/** The floating "Lucka" button: the stored word it converts and where it sits. */
export type MakeGapButton = { gapId: string; from: number; to: number; seed: string; left: number; top: number };

export function useExamWorkspaceMakeGap(options: {
  editor: Ref<Editor | undefined>;
  canMakeGap: () => boolean;
  nextGapId: () => string | null | undefined;
  /** While true, a word click or a drag selection becomes a gap at once. */
  gapTool: () => boolean;
}): {
  makeGapButton: Ref<MakeGapButton | null>;
  makeGapButtonElement: Ref<HTMLButtonElement | null>;
  pendingGapCreation: () => { gapId: string; seed: string } | null;
  makeGap: (gapId: string) => void;
  confirmMakeGap: () => void;
  handleMakeGapClick: (view: EditorView, pos: number, event: MouseEvent) => boolean;
  handleGapToolMouseDown: (event: MouseEvent) => void;
  handleGapToolMouseUp: (event: MouseEvent) => void;
  maybeHideMakeGapButton: (transaction: Transaction) => void;
  hideMakeGap: () => void;
  removeMakeGapListeners: () => void;
} {
  const makeGapButton: Ref<MakeGapButton | null> = ref(null);
  const makeGapButtonElement: Ref<HTMLButtonElement | null> = ref(null);

  /** Set while a gap replacement dispatches, so its one change emits `createGap`. */
  let gapCreation: { gapId: string; seed: string } | null = null;

  function pendingGapCreation(): { gapId: string; seed: string } | null {
    return gapCreation;
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

  /** Place the floating button right after its word, on that word's own line. */
  function placeMakeGapButton(): void {
    const current = makeGapButton.value;
    const view = options.editor.value?.view;
    if (current === null || !view) {
      return;
    }
    let coords: { left: number; top: number; right: number; bottom: number };
    try {
      // The -1 bias keeps the caret on the line where the word ends, so a
      // word ending a line never moves the button to the next line.
      coords = view.coordsAtPos(current.to, -1);
    } catch {
      hideMakeGap();
      return;
    }
    const height = makeGapButtonElement.value?.offsetHeight ?? 0;
    const width = makeGapButtonElement.value?.offsetWidth ?? 0;
    const lineHeight = coords.bottom - coords.top;
    const top = coords.top + (lineHeight - height) / 2;
    const maxLeft = window.innerWidth - width - ANCHORED_EDGE_PX;
    const left =
      maxLeft < ANCHORED_EDGE_PX
        ? ANCHORED_EDGE_PX
        : Math.min(Math.max(coords.right + ANCHORED_GAP_PX, ANCHORED_EDGE_PX), maxLeft);
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

  /**
   * Replace `from`..`to` with one new gap and report one pending creation,
   * never an `update`. The caller owns the range: the selection for the
   * toolbar command, the stored click word for the floating button.
   */
  function replaceRangeWithGap(gapId: string, from: number, to: number, seed: string): void {
    const current = options.editor.value;
    if (!current || !options.canMakeGap()) {
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
   * as one transaction and reports one pending creation, never an `update`.
   */
  function makeGap(gapId: string): void {
    const current = options.editor.value;
    if (!current || !options.canMakeGap()) {
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
      const word = wordRangeAtDocPosition(state.doc, selection.from);
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

  function handleMakeGapClick(view: EditorView, pos: number, event: MouseEvent): boolean {
    hideMakeGap();
    const gapId = options.nextGapId();
    if (!options.canMakeGap() || typeof gapId !== "string") {
      return false;
    }
    if (event instanceof MouseEvent && event.button !== 0) {
      return false;
    }
    if (options.gapTool()) {
      const word = gapToolWordAtPointer(view, pos, event);
      if (word === null) {
        return false;
      }
      replaceRangeWithGap(gapId, word.from, word.to, view.state.doc.textBetween(word.from, word.to, "\n", " "));
      return true;
    }
    const word = wordRangeAtDocPosition(view.state.doc, pos);
    if (word === null) {
      return false;
    }
    const seed = view.state.doc.textBetween(word.from, word.to, "\n", " ");
    showMakeGapButton(gapId, word.from, word.to, seed);
    return false;
  }

  /**
   * The word the pointer hit while the gap tool is on, or null when the
   * pointer is on a separator or its character cannot be told apart. The
   * click position is a caret between two characters; the pointer is on one
   * of those two neighbours exactly when `clientX` lies between that
   * character's left edge (`coordsAtPos` at its start) and its right edge
   * (`coordsAtPos` past its end). A separator hit, an unreadable position
   * and a zero-width character all resolve to nothing, so ProseMirror places
   * the caret instead.
   */
  function gapToolWordAtPointer(
    view: EditorView,
    pos: number,
    event: MouseEvent,
  ): { from: number; to: number } | null {
    const clientX = event.clientX;
    if (!Number.isFinite(clientX)) {
      return null;
    }
    const size = view.state.doc.content.size;
    for (const charPos of [pos, pos - 1]) {
      if (charPos < 0 || charPos + 1 > size) {
        continue;
      }
      let left: number;
      let right: number;
      try {
        left = view.coordsAtPos(charPos, 1).left;
        right = view.coordsAtPos(charPos + 1, -1).left;
      } catch {
        continue;
      }
      if (!Number.isFinite(left) || !Number.isFinite(right) || right <= left) {
        continue;
      }
      if (clientX >= left && clientX < right) {
        return wordRangeAtDocCharacter(view.state.doc, charPos);
      }
    }
    return null;
  }

  /** True after a primary press started in this editor; cleared on every release. */
  let gapToolPrimaryDown = false;

  /** Record a press started in this editor; only a primary press starts a gap gesture. */
  function handleGapToolMouseDown(event: MouseEvent): void {
    gapToolPrimaryDown = event.button === 0;
  }

  /**
   * Convert a drag selection into one gap on release while the gap tool is
   * on, but only for the primary gesture: a primary press in this editor
   * followed by a primary release. A right-click (or any non-primary
   * release) over an existing selection converts nothing and leaves the
   * document unchanged; the browser finishes the selection after mouseup, so
   * the selection is read on the next tick; `makeGap` keeps its guards (one
   * textblock, no atom, non-blank). A plain click leaves an empty selection
   * behind, so it converts nothing here; the click handler owns that path.
   */
  function handleGapToolMouseUp(event: MouseEvent): void {
    const primaryRelease = event.button === 0 && gapToolPrimaryDown;
    gapToolPrimaryDown = false;
    if (!primaryRelease || !options.gapTool()) {
      return;
    }
    setTimeout(() => {
      const current = options.editor.value;
      if (!current) {
        return;
      }
      const { selection } = current.state;
      if (!(selection instanceof TextSelection) || selection.empty) {
        return;
      }
      const gapId = options.nextGapId();
      if (typeof gapId !== "string") {
        return;
      }
      makeGap(gapId);
    }, 0);
  }

  return {
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
  };
}
