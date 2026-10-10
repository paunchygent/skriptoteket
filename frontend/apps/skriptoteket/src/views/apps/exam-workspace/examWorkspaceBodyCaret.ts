/**
 * Exam workspace question-text caret and range guard.
 *
 * Domain purpose:
 *   Decide whether an edit in a question paragraph would touch a gap chip
 *   or image marker, and insert plain text at the caret. Gaps and images
 *   are part of the Exam.net contract, so the editor refuses any edit whose
 *   range covers an atom or whose deletion starts right beside one.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceBodyEditor` in its `beforeinput` and `paste`
 *     handlers.
 *   - Recognizes atoms by `ATOM_ATTRIBUTE` from `examWorkspaceBodySegments`.
 */

import { ATOM_ATTRIBUTE } from "./examWorkspaceBodySegments";

function isAtomNode(node: Node | null): boolean {
  return node instanceof HTMLElement && node.hasAttribute(ATOM_ATTRIBUTE);
}

function isEmptyTextNode(node: Node | null): boolean {
  return node !== null && node.nodeType === Node.TEXT_NODE && (node.textContent ?? "").length === 0;
}

/** Whether a collapsed caret sits directly beside an atom in the delete direction. */
export function caretBesideAtom(
  root: HTMLElement,
  container: Node,
  offset: number,
  backward: boolean,
): boolean {
  let neighbour: Node | null;
  if (container.nodeType === Node.TEXT_NODE) {
    const length = container.textContent?.length ?? 0;
    if (backward ? offset > 0 : offset < length) {
      return false;
    }
    let current: Node = container;
    neighbour = backward ? current.previousSibling : current.nextSibling;
    while (!neighbour && current.parentNode && current.parentNode !== root) {
      current = current.parentNode;
      neighbour = backward ? current.previousSibling : current.nextSibling;
    }
  } else {
    neighbour = backward
      ? (container.childNodes[offset - 1] ?? null)
      : (container.childNodes[offset] ?? null);
  }
  while (isEmptyTextNode(neighbour)) {
    neighbour = backward ? neighbour!.previousSibling : neighbour!.nextSibling;
  }
  return isAtomNode(neighbour);
}

/** The current document selection as live ranges. */
export function selectionRanges(): Range[] {
  const selection = window.getSelection();
  if (!selection) {
    return [];
  }
  const ranges: Range[] = [];
  for (let index = 0; index < selection.rangeCount; index += 1) {
    ranges.push(selection.getRangeAt(index));
  }
  return ranges;
}

/** The ranges an input event will change, falling back to the selection. */
export function liveRangesFor(event: InputEvent): Range[] {
  const targetRanges = typeof event.getTargetRanges === "function" ? event.getTargetRanges() : [];
  const ranges: Range[] = [];
  for (const staticRange of targetRanges) {
    try {
      const range = document.createRange();
      range.setStart(staticRange.startContainer, staticRange.startOffset);
      range.setEnd(staticRange.endContainer, staticRange.endOffset);
      ranges.push(range);
    } catch {
      // A target range outside the document cannot touch our atoms.
    }
  }
  return ranges.length > 0 ? ranges : selectionRanges();
}

/**
 * Whether any range covers an atom in `root`, or, for a delete input type,
 * whether a collapsed caret would delete the atom beside it.
 */
export function rangesTouchAtom(
  root: HTMLElement,
  ranges: Range[],
  inputType: string | null,
): boolean {
  const atoms = Array.from(root.querySelectorAll<HTMLElement>(`[${ATOM_ATTRIBUTE}]`));
  if (atoms.length === 0) {
    return false;
  }
  return ranges.some((range) => {
    if (!range.collapsed) {
      return atoms.some((atom) => range.intersectsNode(atom));
    }
    if (inputType !== null && inputType.startsWith("delete")) {
      const backward = inputType.includes("Backward");
      return caretBesideAtom(root, range.startContainer, range.startOffset, backward);
    }
    return false;
  });
}

/**
 * Replace the selection inside `element` with a plain text node and put the
 * caret after it. Returns false when the selection is outside `element`.
 */
export function insertPlainText(element: HTMLElement, text: string): boolean {
  const range = selectionRanges()[0];
  if (!range || !element.contains(range.commonAncestorContainer)) {
    return false;
  }
  range.deleteContents();
  const textNode = document.createTextNode(text);
  range.insertNode(textNode);
  const selection = window.getSelection();
  const caret = document.createRange();
  caret.setStartAfter(textNode);
  caret.collapse(true);
  selection?.removeAllRanges();
  selection?.addRange(caret);
  return true;
}
