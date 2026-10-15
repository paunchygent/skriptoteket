/**
 * Exam workspace question-body segment helpers.
 *
 * Domain purpose:
 *   Convert between a native exam paragraph (text, gap and asset segments)
 *   and the inline editor's DOM, where text is free text and gaps and
 *   assets are fixed atoms. Gaps and assets are part of the Exam.net
 *   contract, so the editor compares atom sequences to refuse edits that
 *   remove, add or reorder them. Atom labels live in a `data-label`
 *   attribute rendered by CSS, so copying or dragging question text never
 *   carries a gap's accepted answers or the "Bild" marker into the text.
 *   An asset atom with a known URL renders the real image as a child while
 *   the atom keeps its identity and guards; without a URL the atom stays
 *   the "Bild" placeholder instead of claiming a picture that is not
 *   loaded.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceBodyEditor`, which renders `data-label` through
 *     a `::before` rule and passes the asset URL map through.
 *   - Reads shapes from `api/examWorkspace.ts`; the five text marks and
 *     their DOM wrappers live in `examWorkspaceBodyMarks`.
 */

import type { NativeExamBodySegment, NativeExamGap } from "../../../api/examWorkspace";
import { canonicalMarks, createMarkedText, marksFromDom, sameMarks } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";

export type NativeExamAtomSegment = Exclude<NativeExamBodySegment, { kind: "text" }>;

export type BodyTextPart = { kind: "text"; text: string; marks: BodyMark[] };

export type BodyPart = BodyTextPart | { kind: "atom"; segment: NativeExamAtomSegment };

/** Data attribute that marks a gap or asset atom element inside the editor. */
export const ATOM_ATTRIBUTE = "data-atom";
/** Data attribute that marks the trailing line-break sentinel the editor appends. */
export const TRAILING_BREAK_ATTRIBUTE = "data-trailing-break";
/** Data attribute holding an atom's visible label; CSS renders it, so it is not text content. */
export const LABEL_ATTRIBUTE = "data-label";
/** Data attribute marking the real `<img>` a resolved asset atom renders. */
export const ASSET_IMAGE_ATTRIBUTE = "data-asset-image";
/** Visible label of an asset atom whose picture is not loaded. */
export const ASSET_PLACEHOLDER_LABEL = "Bild";

const CHIP_BASE_CLASSES = [
  "mx-0.5",
  "inline-block",
  "cursor-pointer",
  "select-none",
  "border",
  "px-2",
  "align-baseline",
  "text-sm",
  "font-semibold",
  "leading-normal",
  "text-navy",
  "focus-visible:outline",
  "focus-visible:outline-2",
  "focus-visible:outline-offset-2",
  "focus-visible:outline-action/40",
];
const CHIP_FILLED_CLASSES = ["border-navy/35", "bg-panel-muted"];
const CHIP_EMPTY_CLASSES = ["border-warning", "bg-warning/10"];
const ASSET_CLASSES = [
  "mx-0.5",
  "inline-block",
  "max-w-full",
  "select-none",
  "border",
  "border-navy/35",
  "bg-panel-muted",
  "px-2",
  "align-baseline",
  "text-sm",
  "leading-normal",
  "text-navy",
];
const ASSET_IMAGE_CLASSES = ["block", "h-auto", "max-w-full"];

/**
 * Build model segments from editor parts: adjacent text with the same marks
 * merges into one segment, empty text disappears, and atoms keep their
 * identity. Text is never trimmed, because spacing around gaps is part of
 * the question.
 */
export function segmentsFromParts(parts: BodyPart[]): NativeExamBodySegment[] {
  const segments: NativeExamBodySegment[] = [];
  for (const part of parts) {
    if (part.kind === "atom") {
      segments.push(part.segment);
      continue;
    }
    if (part.text.length === 0) {
      continue;
    }
    const marks = canonicalMarks(part.marks);
    const previous = segments[segments.length - 1];
    if (previous && previous.kind === "text" && sameMarks(previous.marks, marks)) {
      segments[segments.length - 1] = {
        kind: "text",
        text: previous.text + part.text,
        marks: previous.marks,
      };
    } else {
      segments.push({ kind: "text", text: part.text, marks });
    }
  }
  return segments;
}

/** Ordered identities of the gap and asset atoms in a paragraph. */
export function atomIds(segments: NativeExamBodySegment[]): string[] {
  return segments.flatMap((segment) => {
    if (segment.kind === "gap") {
      return [`gap:${segment.gap_id}`];
    }
    if (segment.kind === "asset") {
      return [`asset:${segment.asset_id}`];
    }
    return [];
  });
}

export function sameAtomSequence(
  left: NativeExamBodySegment[],
  right: NativeExamBodySegment[],
): boolean {
  const leftIds = atomIds(left);
  const rightIds = atomIds(right);
  return leftIds.length === rightIds.length && leftIds.every((id, index) => id === rightIds[index]);
}

/** Stable comparison key for a paragraph's segments. */
export function segmentsKey(segments: NativeExamBodySegment[]): string {
  return JSON.stringify(segments);
}

/**
 * Stable comparison key for a paragraph's semantic content: text and atoms
 * only, with contiguous text runs merged, so a mark or heading change keeps
 * the same key.
 */
export function contentKey(segments: NativeExamBodySegment[]): string {
  const items: Array<[string, string]> = [];
  for (const segment of segments) {
    if (segment.kind === "text") {
      const previous = items[items.length - 1];
      if (previous && previous[0] === "text") {
        previous[1] += segment.text;
      } else {
        items.push(["text", segment.text]);
      }
      continue;
    }
    items.push([segment.kind, segment.kind === "gap" ? segment.gap_id : segment.asset_id]);
  }
  return JSON.stringify(items);
}

/** Chip text: the accepted answers, or "Lucka N" while the gap has none. */
export function gapChipLabel(gap: NativeExamGap | undefined, gapNumber: number): string {
  if (gap && gap.accepted_values.length > 0) {
    return gap.accepted_values.join(" / ");
  }
  return gapNumber > 0 ? `Lucka ${gapNumber}` : "Lucka";
}

/** Comma-separated input → accepted values: split, trim, drop empty. */
export function parseAcceptedValues(raw: string): string[] {
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
}

function atomSegmentFromElement(element: Element): NativeExamAtomSegment | null {
  const atom = element.getAttribute(ATOM_ATTRIBUTE);
  if (atom === "gap") {
    const gapId = element.getAttribute("data-gap-id");
    return gapId ? { kind: "gap", gap_id: gapId } : null;
  }
  if (atom === "asset") {
    const assetId = element.getAttribute("data-asset-id");
    return assetId ? { kind: "asset", asset_id: assetId } : null;
  }
  return null;
}

function collectParts(root: HTMLElement, node: Node, parts: BodyPart[]): void {
  node.childNodes.forEach((child, index) => {
    if (child.nodeType === Node.TEXT_NODE) {
      parts.push({
        kind: "text",
        text: child.textContent ?? "",
        marks: marksFromDom(root, child),
      });
      return;
    }
    if (child.nodeType !== Node.ELEMENT_NODE) {
      return;
    }
    const element = child as Element;
    if (element.hasAttribute(ATOM_ATTRIBUTE)) {
      const segment = atomSegmentFromElement(element);
      if (segment) {
        parts.push({ kind: "atom", segment });
      }
      return;
    }
    if (element.tagName === "BR") {
      const isTrailing =
        element.hasAttribute(TRAILING_BREAK_ATTRIBUTE) || index === node.childNodes.length - 1;
      if (!isTrailing) {
        parts.push({ kind: "text", text: "\n", marks: marksFromDom(root, element) });
      }
      return;
    }
    if ((element.tagName === "DIV" || element.tagName === "P") && parts.length > 0) {
      // A browser-inserted block starts a new line.
      parts.push({ kind: "text", text: "\n", marks: marksFromDom(root, element) });
    }
    collectParts(root, element, parts);
  });
}

/**
 * Read an editor paragraph element in document order. Text nodes become text
 * with the marks of their ancestors, atom elements become their segment (any
 * atom content is ignored), inner `<br>` elements become line breaks, and the
 * trailing `<br>` sentinel is ignored.
 */
export function partsFromParagraphElement(element: Element): BodyPart[] {
  const parts: BodyPart[] = [];
  if (element instanceof HTMLElement) {
    collectParts(element, element, parts);
  }
  return parts;
}

/** 1-based position of a gap in the item, or 0 when the item has no such gap. */
export function gapNumberIn(gaps: NativeExamGap[], gapId: string): number {
  return gaps.findIndex((gap) => gap.gap_id === gapId) + 1;
}

/**
 * Bring a gap chip's label, accessible name and filled/empty styling in
 * line with the gap. An unchanged chip is left untouched so a nearby caret
 * stays put.
 */
export function applyChipState(chip: HTMLElement, gaps: NativeExamGap[]): void {
  const gapId = chip.getAttribute("data-gap-id") ?? "";
  const gap = gaps.find((candidate) => candidate.gap_id === gapId);
  const number = gapNumberIn(gaps, gapId);
  const label = gapChipLabel(gap, number);
  const isEmpty = !gap || gap.accepted_values.length === 0;
  const warningShown = chip.classList.contains(CHIP_EMPTY_CLASSES[0]!);
  const filledShown = chip.classList.contains(CHIP_FILLED_CLASSES[0]!);
  if (chip.getAttribute(LABEL_ATTRIBUTE) === label && (isEmpty ? warningShown : filledShown)) {
    return;
  }
  chip.setAttribute(LABEL_ATTRIBUTE, label);
  chip.setAttribute(
    "aria-label",
    isEmpty
      ? `Lucka ${number}, saknar godkända svar`
      : `Lucka ${number}, godkända svar: ${label}`,
  );
  chip.classList.remove(...(isEmpty ? CHIP_FILLED_CLASSES : CHIP_EMPTY_CLASSES));
  chip.classList.add(...(isEmpty ? CHIP_EMPTY_CLASSES : CHIP_FILLED_CLASSES));
}

/** Build the non-editable element for a gap chip or an image marker. */
export function createAtomElement(
  segment: NativeExamAtomSegment,
  gaps: NativeExamGap[],
  assetUrls?: Record<string, string>,
  gapInteractive = true,
): HTMLElement {
  const element = document.createElement("span");
  element.setAttribute("contenteditable", "false");
  if (segment.kind === "gap") {
    element.setAttribute(ATOM_ATTRIBUTE, "gap");
    element.setAttribute("data-gap-id", segment.gap_id);
    if (gapInteractive) {
      element.setAttribute("role", "button");
      element.setAttribute("tabindex", "0");
      element.setAttribute("aria-haspopup", "dialog");
      element.setAttribute("aria-expanded", "false");
    }
    element.classList.add(...CHIP_BASE_CLASSES);
    applyChipState(element, gaps);
  } else {
    element.setAttribute(ATOM_ATTRIBUTE, "asset");
    element.setAttribute("data-asset-id", segment.asset_id);
    element.setAttribute("role", "img");
    element.classList.add(...ASSET_CLASSES);
    applyAssetState(element, segment.asset_id, assetUrls);
  }
  return element;
}

/**
 * Bring an asset atom in line with the asset URL map: a known URL renders
 * the actual picture inside the atom, an unknown URL keeps the "Bild"
 * placeholder. Only the atom's own attribute and image child change, so a
 * nearby caret and every sibling node stay in place.
 */
export function applyAssetState(
  element: HTMLElement,
  assetId: string,
  assetUrls?: Record<string, string>,
): void {
  const url = assetUrls?.[assetId];
  const image = element.querySelector<HTMLImageElement>(`img[${ASSET_IMAGE_ATTRIBUTE}]`);
  if (!url) {
    image?.remove();
    element.setAttribute(LABEL_ATTRIBUTE, ASSET_PLACEHOLDER_LABEL);
    element.setAttribute("aria-label", ASSET_PLACEHOLDER_LABEL);
    return;
  }
  element.removeAttribute(LABEL_ATTRIBUTE);
  element.setAttribute("aria-label", ASSET_PLACEHOLDER_LABEL);
  if (image) {
    if (image.getAttribute("src") !== url) {
      image.setAttribute("src", url);
    }
    return;
  }
  element.appendChild(createAssetImage(url));
}

function createAssetImage(url: string): HTMLImageElement {
  const image = document.createElement("img");
  image.setAttribute(ASSET_IMAGE_ATTRIBUTE, "");
  image.setAttribute("src", url);
  image.setAttribute("alt", "");
  image.setAttribute("draggable", "false");
  image.classList.add(...ASSET_IMAGE_CLASSES);
  return image;
}

/** Replace a paragraph element's content with the DOM for its ordered parts. */
export function renderParagraphParts(
  element: HTMLElement,
  parts: BodyPart[],
  gaps: NativeExamGap[],
  assetUrls?: Record<string, string>,
  gapInteractive = true,
): void {
  const nodes: Node[] = parts.map((part) =>
    part.kind === "text"
      ? createMarkedText(part.text, part.marks)
      : createAtomElement(part.segment, gaps, assetUrls, gapInteractive),
  );
  element.replaceChildren(...nodes, createTrailingBreak());
}

/** Replace a paragraph element's content with the DOM for its segments. */
export function renderParagraphElement(
  element: HTMLElement,
  segments: NativeExamBodySegment[],
  gaps: NativeExamGap[],
  assetUrls?: Record<string, string>,
  gapInteractive = true,
): void {
  renderParagraphParts(
    element,
    segments.map((segment) =>
      segment.kind === "text"
        ? { kind: "text" as const, text: segment.text, marks: segment.marks }
        : { kind: "atom" as const, segment },
    ),
    gaps,
    assetUrls,
    gapInteractive,
  );
}

function createTrailingBreak(): HTMLElement {
  const sentinel = document.createElement("br");
  sentinel.setAttribute(TRAILING_BREAK_ATTRIBUTE, "");
  return sentinel;
}

/** Keep exactly one trailing `<br>` sentinel so a final newline stays visible. */
export function ensureTrailingBreak(element: HTMLElement): void {
  const last = element.lastChild;
  if (last instanceof HTMLElement && last.hasAttribute(TRAILING_BREAK_ATTRIBUTE)) {
    return;
  }
  element.querySelectorAll(`[${TRAILING_BREAK_ATTRIBUTE}]`).forEach((stale) => stale.remove());
  element.appendChild(createTrailingBreak());
}

/** Keep chip `data-test` indexes aligned with the paragraph's current segments. */
export function refreshAtomIndexes(
  element: HTMLElement,
  paragraphIndex: number,
  segments: NativeExamBodySegment[],
): void {
  const atoms = Array.from(element.querySelectorAll<HTMLElement>(`[${ATOM_ATTRIBUTE}]`));
  let atomPosition = 0;
  segments.forEach((segment, segmentIndex) => {
    if (segment.kind === "text") {
      return;
    }
    const atom = atoms[atomPosition];
    atomPosition += 1;
    if (atom && segment.kind === "gap") {
      atom.setAttribute("data-test", `exam-workspace-body-gap-${paragraphIndex}-${segmentIndex}`);
    }
  });
}
