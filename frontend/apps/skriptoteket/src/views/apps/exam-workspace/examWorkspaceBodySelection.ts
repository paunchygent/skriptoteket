/**
 * Exam workspace paragraph selection offsets.
 *
 * Domain purpose:
 *   Map the browser selection onto a paragraph's flat character offsets — a
 *   gap chip or picture counts as one character — and back after the
 *   paragraph DOM is rebuilt for a mark toggle. Offsets let the teacher
 *   toggle the same selection repeatedly without losing it, because the
 *   text stays byte-for-byte the same across the rebuild.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceBodyParagraph` around `withToggledMark`.
 *   - Recognizes atoms by `ATOM_ATTRIBUTE` from `examWorkspaceBodySegments`.
 */

import { ATOM_ATTRIBUTE } from "./examWorkspaceBodySegments";

export type ParagraphSelection = { start: number; end: number };

type TextCell = { kind: "text"; node: Text; start: number; end: number };
type AtomCell = { kind: "atom"; element: HTMLElement; start: number; end: number };
type Cell = TextCell | AtomCell;

function cellNode(cell: Cell): Node {
  return cell.kind === "text" ? cell.node : cell.element;
}

/** Every text and atom position in document order; an atom occupies one offset. */
function cellsOf(root: HTMLElement): Cell[] {
  const cells: Cell[] = [];
  let offset = 0;
  const walk = (node: Node): void => {
    node.childNodes.forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        const text = child as Text;
        cells.push({ kind: "text", node: text, start: offset, end: offset + text.data.length });
        offset += text.data.length;
        return;
      }
      if (!(child instanceof HTMLElement)) {
        return;
      }
      if (child.hasAttribute(ATOM_ATTRIBUTE)) {
        cells.push({ kind: "atom", element: child, start: offset, end: offset + 1 });
        offset += 1;
        return;
      }
      if (child.tagName === "BR") {
        return;
      }
      walk(child);
    });
  };
  walk(root);
  return cells;
}

function offsetAt(cells: Cell[], container: Node, offset: number): number {
  if (container.nodeType === Node.TEXT_NODE) {
    const cell = cells.find(
      (entry): entry is TextCell => entry.kind === "text" && entry.node === container,
    );
    return cell ? cell.start + Math.min(offset, cell.end - cell.start) : 0;
  }
  const element = container as Element;
  const boundary = element.childNodes[offset] ?? null;
  if (boundary === null) {
    const contained = cells.filter((cell) => element.contains(cellNode(cell)));
    return contained[contained.length - 1]?.end ?? 0;
  }
  const first = cells.find((cell) => boundary === cellNode(cell) || boundary.contains(cellNode(cell)));
  return first?.start ?? cells[cells.length - 1]?.end ?? 0;
}

export function offsetsForRange(root: HTMLElement, range: Range): ParagraphSelection {
  const cells = cellsOf(root);
  return {
    start: offsetAt(cells, range.startContainer, range.startOffset),
    end: offsetAt(cells, range.endContainer, range.endOffset),
  };
}

/** The current selection as paragraph offsets, or null when it sits outside `root`. */
export function selectionOffsets(root: HTMLElement): ParagraphSelection | null {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return null;
  }
  const range = selection.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) {
    return null;
  }
  return offsetsForRange(root, range);
}

function boundaryOf(element: HTMLElement, before: boolean): { node: Node; offset: number } | null {
  const parent = element.parentNode;
  if (!parent) {
    return null;
  }
  const index = Array.prototype.indexOf.call(parent.childNodes, element);
  return { node: parent, offset: before ? index : index + 1 };
}

function positionAt(cells: Cell[], offset: number, side: "start" | "end"): { node: Node; offset: number } | null {
  for (const cell of cells) {
    if (cell.kind === "text") {
      if (offset <= cell.start) {
        return { node: cell.node, offset: 0 };
      }
      if (offset < cell.end) {
        return { node: cell.node, offset: offset - cell.start };
      }
      if (offset === cell.end && side === "end") {
        return { node: cell.node, offset: cell.end - cell.start };
      }
      continue;
    }
    if (offset <= cell.start) {
      return boundaryOf(cell.element, true);
    }
    if (offset < cell.end) {
      return boundaryOf(cell.element, true);
    }
    if (offset === cell.end && side === "end") {
      return boundaryOf(cell.element, false);
    }
  }
  const last = cells[cells.length - 1];
  if (!last) {
    return null;
  }
  return last.kind === "text"
    ? { node: last.node, offset: last.end - last.start }
    : boundaryOf(last.element, false);
}

/** The range covering the flat `[start, end)` selection, or null when the paragraph has no text. */
export function rangeFromOffsets(root: HTMLElement, selection: ParagraphSelection): Range | null {
  const cells = cellsOf(root);
  if (cells.length === 0) {
    return null;
  }
  const start = positionAt(cells, Math.max(0, selection.start), "start");
  const end = positionAt(cells, Math.max(selection.end, selection.start), "end");
  if (!start || !end) {
    return null;
  }
  const range = document.createRange();
  try {
    range.setStart(start.node, start.offset);
    range.setEnd(end.node, end.offset);
  } catch {
    return null;
  }
  return range;
}
