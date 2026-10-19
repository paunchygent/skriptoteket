/**
 * Exam workspace make-gap command, the Tom lucka command and the empty gap's
 * definition.
 *
 * Domain purpose:
 *   The one place that turns written text into a gap: the word at the
 *   caret, or the selected range, becomes one gap atom in one transaction,
 *   seeded from the replaced document text. The caret ends collapsed
 *   directly after the new chip, so typing continues after the gap and never
 *   replaces it. A caret outside a word creates
 *   nothing. Tom lucka is the only empty-gap path: one empty gap at the
 *   caret, or at a selection's end without deleting text. While the gap tool is on, a
 *   word click converts at once through the same replacement and a drag
 *   selection converts on mouseup. A tool click converts only the word the
 *   pointer actually hit (a click on a space or punctuation only places the
 *   caret), and a release converts only after a primary press started in
 *   this editor, so a right-click over a selection never makes a gap. A tool
 *   click on a word that keeps hidden answers reports its kept link through
 *   `keptGapAtPointer` instead of making a gap, and a double-click press on
 *   a kept word restores through `keptGapAtDoubleClick` instead. The
 *   gap tool switch is the only gap control for existing text.
 *
 * Relationships:
 *   - Wired in by `ExamWorkspaceRichTextEditor`, which owns the editor and
 *     the `createGap` emit boundary.
 *   - Resolves words with `examWorkspaceGapWord`.
 *   - The selection layer consumes `bodyWithoutEmptyGaps` for the silent
 *     empty-gap cleanup when the teacher leaves the question.
 */

import type { Editor } from "@tiptap/core";
import type { Mark } from "@tiptap/pm/model";
import { TextSelection } from "@tiptap/pm/state";
import type { EditorView } from "@tiptap/pm/view";
import type { Ref } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { bodyWithoutGap, gapHasAnswer } from "./examWorkspaceGapEdits";
import { hasKeyedOrigin } from "./examWorkspaceAnswerKeyRules";
import { EXAM_GAP_NODE, EXAM_KEPT_GAP_MARK, EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";
import { wordRangeAtDocCharacter, wordRangeAtDocPosition } from "./examWorkspaceGapWord";

/** A kept link the pointer hit: its kept id and the clicked block's index. */
export type KeptGapHit = { keptGapId: string; blockIndex: number };

/** Why Tom lucka is unavailable when there is no next gap id. */
export const EMPTY_GAP_AT_CAP_REASON = "Tom lucka – inga fler luckor kan läggas till i frågan";

/**
 * Why the Tom lucka command is unavailable: there is no next gap id. Null
 * while the command can run. A question that is not a gap question never
 * reaches this reason: its button does not render, and the body editor
 * refuses the command with its own kind guard and no copy.
 */
export function gapDisabledReason(nextGapId: string | null | undefined): string | null {
  if (typeof nextGapId !== "string") {
    return EMPTY_GAP_AT_CAP_REASON;
  }
  return null;
}

/**
 * The item's empty gaps in gap order (TASK-SKRIPT-40-04-13 Q9): a Lucktext
 * gap with no accepted answer in a question that has an answer key, or a
 * dropdown gap with no correct option. The answer half reuses `gapHasAnswer`;
 * a question without an answer key, or any other kind, has none. The
 * key-presence check is the canonical `hasKeyedOrigin` from
 * `examWorkspaceAnswerKeyRules`.
 */
export function emptyGapIds(item: NativeExamItem): string[] {
  if (item.kind !== "gap_fill" && item.kind !== "inline_choice") {
    return [];
  }
  if (!hasKeyedOrigin(item)) {
    return [];
  }
  return item.gaps
    .filter((gap) => !gapHasAnswer(gap, item.kind))
    .map((gap) => gap.gap_id);
}

/**
 * The body with every empty gap's placement removed, for the silent cleanup
 * when the teacher leaves the question. Null when there is nothing to
 * remove, so the cleanup emits no edit. The owner drops each removed gap's
 * record through `withBody`, so one structural edit removes them in one undo
 * step.
 */
export function bodyWithoutEmptyGaps(
  item: NativeExamItem,
): NativeExamBodyParagraph[] | null {
  const ids = emptyGapIds(item);
  if (ids.length === 0) {
    return null;
  }
  return ids.reduce<NativeExamBodyParagraph[]>(
    (body, gapId) => bodyWithoutGap(body, gapId),
    [...item.body],
  );
}

export function useExamWorkspaceMakeGap(options: {
  editor: Ref<Editor | undefined>;
  canMakeGap: () => boolean;
  nextGapId: () => string | null | undefined;
  /** While true, a word click or a drag selection becomes a gap at once. */
  gapTool: () => boolean;
}): {
  pendingGapCreation: () => { gapId: string; seed: string } | null;
  makeGap: (gapId: string) => void;
  /** Tom lucka: insert one empty gap at the caret or at the selection's end. */
  insertEmptyGapAtCursor: (gapId: string) => void;
  handleMakeGapClick: (view: EditorView, pos: number, event: MouseEvent) => boolean;
  handleGapToolMouseDown: (event: MouseEvent) => void;
  handleGapToolMouseUp: (event: MouseEvent) => void;
  keptGapAtPointer: (view: EditorView, pos: number, event: MouseEvent) => KeptGapHit | null;
  keptGapAtDoubleClick: (view: EditorView, pos: number, event: MouseEvent) => KeptGapHit | null;
} {
  /** Set while a gap replacement dispatches, so its one change emits `createGap`. */
  let gapCreation: { gapId: string; seed: string } | null = null;

  function pendingGapCreation(): { gapId: string; seed: string } | null {
    return gapCreation;
  }

  /**
   * Replace `from`..`to` with one new gap and report one pending creation,
   * never an `update`. The caller owns the range: the selection, or the
   * word the gap tool hit. The caret ends collapsed directly after the new
   * chip, so typing continues after the gap and never replaces it; a
   * tool-made gap opens no popover.
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
    const withCaretAfter = replaced.setSelection(TextSelection.create(replaced.doc, from + 1));
    gapCreation = { gapId, seed };
    try {
      current.view.dispatch(withCaretAfter);
    } finally {
      gapCreation = null;
    }
  }

  /**
   * Turn the selection, or the word at the caret, into one new gap with
   * `gapId`. A caret outside a word creates nothing (Tom lucka owns the one
   * empty-gap path). The replacement dispatches as one transaction and reports
   * one pending creation, never an `update`.
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
      }
    }
  }

  /**
   * Tom lucka: insert one empty gap at the caret, or at a selection's end
   * without deleting text, with `gapId`. The insertion dispatches as one
   * transaction and reports one pending creation with an empty seed, never an
   * `update`, so the owner adds the empty record through `withNewGap` and the
   * new gap's popover opens at once. It works with the gap tool on or off; a
   * selection across two paragraphs inserts nothing.
   */
  function insertEmptyGapAtCursor(gapId: string): void {
    const current = options.editor.value;
    if (!current || !options.canMakeGap()) {
      return;
    }
    const { selection } = current.state;
    if (!(selection instanceof TextSelection)) {
      return;
    }
    if (selection.empty) {
      replaceRangeWithGap(gapId, selection.from, selection.from, "");
      return;
    }
    const { $from, $to } = selection;
    if (!$from.sameParent($to) || !$to.parent.isTextblock) {
      return;
    }
    replaceRangeWithGap(gapId, $to.pos, $to.pos, "");
  }

  /** A tool-off click only places the caret: the tool is the only gap control. */
  function handleMakeGapClick(view: EditorView, pos: number, event: MouseEvent): boolean {
    if (event instanceof MouseEvent && event.detail > 1) {
      return false;
    }
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
    return false;
  }

  /**
   * The pointer-hit document character while the gap tool is on, or null
   * when the pointer is on a separator or its character cannot be told
   * apart. The click position is a caret between two characters; the pointer
   * is on one of those two neighbours exactly when `clientX` lies between
   * that character's two caret edges (`coordsAtPos` at its start and past its
   * end). Either edge may sit left on screen: in a right-to-left run the
   * start caret is right of the end caret. A separator hit, an unreadable
   * position and a zero-width character all resolve to nothing, so
   * ProseMirror places the caret instead.
   */
  function pointerHitChar(view: EditorView, pos: number, event: MouseEvent): number | null {
    const clientX = event.clientX;
    if (!Number.isFinite(clientX)) {
      return null;
    }
    const size = view.state.doc.content.size;
    for (const charPos of [pos, pos - 1]) {
      if (charPos < 0 || charPos + 1 > size) {
        continue;
      }
      let firstEdge: number;
      let secondEdge: number;
      try {
        firstEdge = view.coordsAtPos(charPos, 1).left;
        secondEdge = view.coordsAtPos(charPos + 1, -1).left;
      } catch {
        continue;
      }
      if (!Number.isFinite(firstEdge) || !Number.isFinite(secondEdge) || firstEdge === secondEdge) {
        continue;
      }
      const hitStart = Math.min(firstEdge, secondEdge);
      const hitEnd = Math.max(firstEdge, secondEdge);
      if (clientX >= hitStart && clientX < hitEnd) {
        return charPos;
      }
    }
    return null;
  }

  /**
   * The word the pointer hit while the gap tool is on, or null when the
   * pointer hit no word character. The pointer check is `pointerHitChar`;
   * the word around it comes from `examWorkspaceGapWord`.
   */
  function gapToolWordAtPointer(
    view: EditorView,
    pos: number,
    event: MouseEvent,
  ): { from: number; to: number } | null {
    const charPos = pointerHitChar(view, pos, event);
    if (charPos === null) {
      return null;
    }
    return wordRangeAtDocCharacter(view.state.doc, charPos);
  }

  /** Whether a ProseMirror node's marks carry the kept link `keptGapId`. */
  function carriesKeptLink(node: { marks: readonly Mark[] }, keptGapId: string): boolean {
    return node.marks.some(
      (mark) => mark.type.name === EXAM_KEPT_GAP_MARK && mark.attrs.keptGapId === keptGapId,
    );
  }

  /**
   * The kept link the pointer hit while the gap tool is on: its kept id and
   * the clicked block's index among that id's contiguous kept blocks in
   * document order, matching the block order `withKeptGapRestored` restores
   * from. Null while the tool is off, on a non-primary button, when the
   * pointer hit no kept character, or on the second press of a double click
   * (that press carries click count 2 and reaches the editor through
   * `handleDoubleClick` instead; see `keptGapAtDoubleClick`).
   */
  function keptGapAtPointer(view: EditorView, pos: number, event: MouseEvent): KeptGapHit | null {
    if (!options.gapTool()) {
      return null;
    }
    if (event instanceof MouseEvent && (event.button !== 0 || event.detail > 1)) {
      return null;
    }
    return keptGapHitAtClick(view, pos, event);
  }

  /**
   * The kept link under a double-click press while the gap tool is on.
   * ProseMirror classifies a press within 500 ms and 10 px of the previous
   * one as a double click and routes it to `handleDoubleClick`, never to
   * `handleClick`, so without this path a kept-word click that lands fast on
   * the reverted chip's spot would only place the caret. The press carries
   * click count 2, so the single-click detail guard must not apply; a press
   * on anything but a kept word still resolves to nothing, so a real double
   * click never makes a gap and then reverts it.
   */
  function keptGapAtDoubleClick(view: EditorView, pos: number, event: MouseEvent): KeptGapHit | null {
    if (!options.gapTool()) {
      return null;
    }
    if (event instanceof MouseEvent && event.button !== 0) {
      return null;
    }
    return keptGapHitAtClick(view, pos, event);
  }

  /**
   * The shared pointer-hit core behind `keptGapAtPointer` and
   * `keptGapAtDoubleClick`: the kept link at the click's document position,
   * resolved through the pointer's character column, with the clicked
   * block's index in document order. Callers own the press-count guard.
   */
  function keptGapHitAtClick(view: EditorView, pos: number, event: MouseEvent): KeptGapHit | null {
    const charPos = pointerHitChar(view, pos, event);
    if (charPos === null) {
      return null;
    }
    let hit: string | null = null;
    view.state.doc.nodesBetween(charPos, charPos + 1, (node) => {
      if (!node.isText) {
        return true;
      }
      for (const mark of node.marks) {
        if (mark.type.name === EXAM_KEPT_GAP_MARK && typeof mark.attrs.keptGapId === "string") {
          hit = mark.attrs.keptGapId;
          return false;
        }
      }
      return false;
    });
    if (hit === null) {
      return null;
    }
    const keptGapId: string = hit;
    let current = -1;
    let clicked = -1;
    let inBlock = false;
    view.state.doc.descendants((node, nodePos) => {
      if (node.isTextblock) {
        inBlock = false;
        return true;
      }
      if (node.type.name === "hardBreak") {
        if (!carriesKeptLink(node, keptGapId)) {
          inBlock = false;
        }
        return false;
      }
      if (node.isText) {
        if (carriesKeptLink(node, keptGapId)) {
          if (!inBlock) {
            current += 1;
            inBlock = true;
          }
          const length = node.text?.length ?? 0;
          if (nodePos <= charPos && charPos < nodePos + length) {
            clicked = current;
          }
        } else {
          inBlock = false;
        }
        return false;
      }
      if (node.isAtom) {
        inBlock = false;
        return false;
      }
      return true;
    });
    if (clicked < 0) {
      return null;
    }
    return { keptGapId, blockIndex: clicked };
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
    pendingGapCreation,
    makeGap,
    insertEmptyGapAtCursor,
    handleMakeGapClick,
    handleGapToolMouseDown,
    handleGapToolMouseUp,
    keptGapAtPointer,
    keptGapAtDoubleClick,
  };
}
