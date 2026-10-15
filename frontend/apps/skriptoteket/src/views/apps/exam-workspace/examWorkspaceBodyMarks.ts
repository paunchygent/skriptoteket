/**
 * Exam workspace rich-text marks.
 *
 * Domain purpose:
 *   The five marks the native document keeps (bold, italic, underline,
 *   superscript, subscript) as DOM wrappers, readers and one selection
 *   toggle. A mark is a nested element around a range of text, never a
 *   styling instruction: typing inside the element keeps the mark, and
 *   serializing reads the marks back off the ancestors. Superscript and
 *   subscript exclude each other, because one glyph cannot sit both above
 *   and below the baseline.
 *
 * Relationships:
 *   - `ExamWorkspaceBodyParagraph` renders text through `createMarkedText`
 *     and toggles a selection through `withToggledMark`.
 *   - `examWorkspaceBodySegments` reads marks back with `marksFromDom` and
 *     owns the `BodyPart` shape this module transforms.
 *   - `ExamWorkspaceMarkToolbar` takes its glyph labels from here.
 */

import type { BodyPart } from "./examWorkspaceBodySegments";

/** Every mark the native document stores, in the order a toolbar shows them. */
export const BODY_MARKS = ["bold", "italic", "underline", "superscript", "subscript"] as const;

export type BodyMark = (typeof BODY_MARKS)[number];

/** The HTML element each mark renders as, so export tags and editor tags agree. */
export const MARK_TAGS: Record<BodyMark, "strong" | "em" | "u" | "sup" | "sub"> = {
  bold: "strong",
  italic: "em",
  underline: "u",
  superscript: "sup",
  subscript: "sub",
};

/** The Swedish action name for a mark button's tooltip and accessible name. */
export const MARK_LABELS: Record<BodyMark, string> = {
  bold: "Fet",
  italic: "Kursiv",
  underline: "Understruken",
  superscript: "Upphöjd",
  subscript: "Nedsänkt",
};

/** The mark that adding a mark replaces: one glyph cannot sit both above and below the baseline. */
const EXCLUDED_MARK: Partial<Record<BodyMark, BodyMark>> = {
  superscript: "subscript",
  subscript: "superscript",
};

const TAG_MARKS = new Map<string, BodyMark>([
  ["STRONG", "bold"],
  ["B", "bold"],
  ["EM", "italic"],
  ["I", "italic"],
  ["U", "underline"],
  ["SUP", "superscript"],
  ["SUB", "subscript"],
]);

function isBodyMark(value: string | null): value is BodyMark {
  return value !== null && (BODY_MARKS as readonly string[]).includes(value);
}

/** Marks without duplicates, in the canonical toolbar order. */
export function canonicalMarks(marks: Iterable<BodyMark>): BodyMark[] {
  const unique = new Set(marks);
  return BODY_MARKS.filter((mark) => unique.has(mark));
}

export function sameMarks(left: readonly BodyMark[], right: readonly BodyMark[]): boolean {
  return left.length === right.length && left.every((mark, index) => mark === right[index]);
}

/** Wrap `text` in one element per mark, outermost first, and return the node. */
export function createMarkedText(text: string, marks: Iterable<BodyMark>): Node {
  const textNode = document.createTextNode(text);
  const wrappers = [...canonicalMarks(marks)];
  return wrappers.reduceRight<Node>((child, mark) => {
    const wrapper = document.createElement(MARK_TAGS[mark]);
    wrapper.setAttribute("data-mark", mark);
    wrapper.append(child);
    return wrapper;
  }, textNode);
}

/** Every mark the node inherits between itself and `root`, in canonical order. */
export function marksFromDom(root: HTMLElement, node: Node): BodyMark[] {
  const marks = new Set<BodyMark>();
  let current: Node | null = node.parentNode;
  while (current && current !== root) {
    if (current instanceof Element) {
      const byTag = TAG_MARKS.get(current.tagName);
      const byAttribute = current.getAttribute("data-mark");
      const mark = byTag ?? (isBodyMark(byAttribute) ? byAttribute : null);
      if (mark) {
        marks.add(mark);
      }
    }
    current = current.parentNode;
  }
  return canonicalMarks(marks);
}

function partLength(part: BodyPart): number {
  return part.kind === "text" ? part.text.length : 1;
}

/**
 * The marks every covered character carries, or the marks at a collapsed
 * caret, for the toolbar's pressed state.
 */
export function marksForOffsets(parts: BodyPart[], start: number, end: number): BodyMark[] {
  let offset = 0;
  const covered: BodyMark[][] = [];
  let careted: BodyMark[] | null = null;
  for (const part of parts) {
    if (part.kind === "text") {
      const partStart = offset;
      const partEnd = offset + part.text.length;
      if (end > start && partEnd > start && partStart < end) {
        covered.push(part.marks);
      }
      if (start === end && start >= partStart && start <= partEnd) {
        careted = part.marks;
      }
    }
    offset += partLength(part);
  }
  if (covered.length > 0) {
    return BODY_MARKS.filter((mark) => covered.every((marks) => marks.includes(mark)));
  }
  return careted ?? [];
}

/** The marks a covered fragment keeps after the toggle: add, or remove, and drop the excluded mark. */
function toggledMarks(marks: BodyMark[], mark: BodyMark, adding: boolean): BodyMark[] {
  const kept = marks.filter(
    (current) => current !== mark && (adding ? EXCLUDED_MARK[mark] !== current : true),
  );
  return canonicalMarks(adding ? [...kept, mark] : kept);
}

/**
 * Apply or remove one mark over the flat `[start, end)` range, splitting
 * text parts at both boundaries. Returns the new parts, or null when the
 * range covers no text (a collapsed caret or atoms only).
 */
export function withToggledMark(
  parts: BodyPart[],
  start: number,
  end: number,
  mark: BodyMark,
): BodyPart[] | null {
  let offset = 0;
  let covered = 0;
  let allMarked = true;
  for (const part of parts) {
    const from = Math.max(start, offset);
    const to = Math.min(end, offset + partLength(part));
    if (part.kind === "text" && to > from) {
      covered += to - from;
      if (!part.marks.includes(mark)) {
        allMarked = false;
      }
    }
    offset += partLength(part);
  }
  if (covered === 0) {
    return null;
  }
  const adding = !allMarked;
  const next: BodyPart[] = [];
  offset = 0;
  for (const part of parts) {
    const from = Math.max(start, offset);
    const to = Math.min(end, offset + partLength(part));
    if (part.kind === "atom" || to <= from) {
      next.push(part);
      offset += partLength(part);
      continue;
    }
    const localFrom = from - offset;
    const localTo = to - offset;
    const head = part.text.slice(0, localFrom);
    const middle = part.text.slice(localFrom, localTo);
    const tail = part.text.slice(localTo);
    if (head.length > 0) {
      next.push({ kind: "text", text: head, marks: part.marks });
    }
    next.push({ kind: "text", text: middle, marks: toggledMarks(part.marks, mark, adding) });
    if (tail.length > 0) {
      next.push({ kind: "text", text: tail, marks: part.marks });
    }
    offset += partLength(part);
  }
  return next;
}
