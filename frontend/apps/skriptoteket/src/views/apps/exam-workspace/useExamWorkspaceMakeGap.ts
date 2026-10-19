/**
 * Exam workspace make-gap command and floating gap button.
 *
 * Domain purpose:
 *   The one place that turns a word into a gap: the shared toolbar's Lucka
 *   command (the selection, or the word at the caret) and the small floating
 *   "Lucka" button ("Gör till lucka" tooltip and accessible name) above a
 *   clicked word. Both paths resolve the word with the same whole-textblock
 *   resolver in document positions, replace it with one gap atom in one
 *   transaction, and seed the gap from the replaced document text. The button
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
import { wordRangeAtDocPosition } from "./examWorkspaceGapWord";
import { ANCHORED_EDGE_PX, ANCHORED_GAP_PX } from "./useExamWorkspaceAnchoredPosition";

/** The floating "Lucka" button: the stored word it converts and where it sits. */
export type MakeGapButton = { gapId: string; from: number; to: number; seed: string; left: number; top: number };

export function useExamWorkspaceMakeGap(options: {
  editor: Ref<Editor | undefined>;
  canMakeGap: () => boolean;
  nextGapId: () => string | null | undefined;
}): {
  makeGapButton: Ref<MakeGapButton | null>;
  makeGapButtonElement: Ref<HTMLButtonElement | null>;
  pendingGapCreation: () => { gapId: string; seed: string } | null;
  makeGap: (gapId: string) => void;
  confirmMakeGap: () => void;
  handleMakeGapClick: (view: EditorView, pos: number, event: MouseEvent) => boolean;
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

  /** Place the floating button above its word, or below it when there is no room above. */
  function placeMakeGapButton(): void {
    const current = makeGapButton.value;
    const view = options.editor.value?.view;
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
    const word = wordRangeAtDocPosition(view.state.doc, pos);
    if (word === null) {
      return false;
    }
    showMakeGapButton(gapId, word.from, word.to, view.state.doc.textBetween(word.from, word.to, "\n", " "));
    return false;
  }

  return {
    makeGapButton,
    makeGapButtonElement,
    pendingGapCreation,
    makeGap,
    confirmMakeGap,
    handleMakeGapClick,
    maybeHideMakeGapButton,
    hideMakeGap,
    removeMakeGapListeners,
  };
}
