<script setup lang="ts">
/**
 * Exam workspace question-text editor.
 *
 * Domain purpose:
 *   Let the teacher edit each paragraph of a question as one continuous
 *   text, with every gap shown as an inline chip and every image as a fixed
 *   "Bild" marker. Activating a gap chip opens a small popover where the
 *   teacher edits that gap's accepted answers. Gaps and images are the
 *   Exam.net contract, so typing, pasting, cutting, dragging or undo can
 *   never remove, add or reorder them.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceItemEditor` for the selected item.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state
 *     (`updateItemParagraphSegments`, `updateItemGapValues`).
 *   - Paragraph DOM is built imperatively from the model so the caret stays
 *     put while the teacher types; `examWorkspaceBodySegments` converts
 *     between that DOM and model segments.
 */

import { computed, nextTick, onMounted, ref, watch } from "vue";
import type { ComponentPublicInstance } from "vue";

import type { NativeExamBodySegment, NativeExamItem } from "../../../api/examWorkspace";
import {
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";
import {
  ATOM_ATTRIBUTE,
  gapChipLabel,
  parseAcceptedValues,
  partsFromParagraphElement,
  sameAtomSequence,
  segmentsFromParts,
  segmentsKey,
  TRAILING_BREAK_ATTRIBUTE,
} from "./examWorkspaceBodySegments";
import type { NativeExamAtomSegment } from "./examWorkspaceBodySegments";

const ATOM_GUARD_COPY = "Luckor och bilder kan inte tas bort i texten.";
const EMPTY_PARAGRAPH_COPY = "Stycket måste innehålla text.";

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

const props = defineProps<{
  item: NativeExamItem;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  updateParagraphSegments: [itemId: string, paragraphIndex: number, segments: NativeExamBodySegment[]];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
}>();

type OpenGap = { gapId: string; top: number; left: number };

const editableMode = detectEditableMode();
const editorRoot = ref<HTMLElement | null>(null);
const popoverInput = ref<HTMLInputElement | null>(null);
const statusMessage = ref<string | null>(null);
const openGap = ref<OpenGap | null>(null);

const hasPartialGapKey = computed(() => isPartiallyKeyedGapItem(props.item));
const openGapModel = computed(() =>
  openGap.value === null
    ? null
    : (props.item.gaps.find((gap) => gap.gap_id === openGap.value?.gapId) ?? null),
);
const openGapNumber = computed(() =>
  openGap.value === null ? 0 : gapNumber(openGap.value.gapId),
);

// Imperative paragraph state; deliberately not reactive.
const paragraphElements: (HTMLElement | null)[] = [];
const renderedKeys: (string | undefined)[] = [];
let renderedItemId: string | null = null;
let openChip: HTMLElement | null = null;

function detectEditableMode(): "plaintext-only" | "true" {
  if (typeof document === "undefined") {
    return "true";
  }
  try {
    const probe = document.createElement("div");
    probe.contentEditable = "plaintext-only";
    return probe.contentEditable === "plaintext-only" ? "plaintext-only" : "true";
  } catch {
    return "true";
  }
}

function setParagraphElement(
  paragraphIndex: number,
  element: Element | ComponentPublicInstance | null,
): void {
  paragraphElements[paragraphIndex] = element instanceof HTMLElement ? element : null;
}

function gapNumber(gapId: string): number {
  return props.item.gaps.findIndex((gap) => gap.gap_id === gapId) + 1;
}

function applyChipState(chip: HTMLElement): void {
  const gapId = chip.getAttribute("data-gap-id") ?? "";
  const gap = props.item.gaps.find((candidate) => candidate.gap_id === gapId);
  const number = gapNumber(gapId);
  const label = gapChipLabel(gap, number);
  const isEmpty = !gap || gap.accepted_values.length === 0;
  const warningShown = chip.classList.contains(CHIP_EMPTY_CLASSES[0]!);
  const filledShown = chip.classList.contains(CHIP_FILLED_CLASSES[0]!);
  if (chip.textContent === label && (isEmpty ? warningShown : filledShown)) {
    // Unchanged: leave the chip's text node alone so a nearby caret stays put.
    return;
  }
  chip.textContent = label;
  chip.setAttribute(
    "aria-label",
    isEmpty
      ? `Lucka ${number}, saknar godkända svar`
      : `Lucka ${number}, godkända svar: ${label}`,
  );
  chip.classList.remove(...(isEmpty ? CHIP_FILLED_CLASSES : CHIP_EMPTY_CLASSES));
  chip.classList.add(...(isEmpty ? CHIP_EMPTY_CLASSES : CHIP_FILLED_CLASSES));
}

function createAtomElement(segment: NativeExamAtomSegment): HTMLElement {
  const element = document.createElement("span");
  element.setAttribute("contenteditable", "false");
  if (segment.kind === "gap") {
    element.setAttribute(ATOM_ATTRIBUTE, "gap");
    element.setAttribute("data-gap-id", segment.gap_id);
    element.setAttribute("role", "button");
    element.setAttribute("tabindex", "0");
    element.setAttribute("aria-haspopup", "dialog");
    element.setAttribute("aria-expanded", "false");
    element.classList.add(...CHIP_BASE_CLASSES);
    applyChipState(element);
  } else {
    element.setAttribute(ATOM_ATTRIBUTE, "asset");
    element.setAttribute("data-asset-id", segment.asset_id);
    element.classList.add(...ASSET_CLASSES);
    element.textContent = "Bild";
  }
  return element;
}

function createTrailingBreak(): HTMLElement {
  const sentinel = document.createElement("br");
  sentinel.setAttribute(TRAILING_BREAK_ATTRIBUTE, "");
  return sentinel;
}

function ensureTrailingBreak(element: HTMLElement): void {
  const last = element.lastChild;
  if (last instanceof HTMLElement && last.hasAttribute(TRAILING_BREAK_ATTRIBUTE)) {
    return;
  }
  element.querySelectorAll(`[${TRAILING_BREAK_ATTRIBUTE}]`).forEach((stale) => stale.remove());
  element.appendChild(createTrailingBreak());
}

/** Keep chip `data-test` indexes aligned with the paragraph's current segments. */
function refreshAtomIndexes(
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
      atom.setAttribute(
        "data-test",
        `exam-workspace-body-gap-${paragraphIndex}-${segmentIndex}`,
      );
    }
  });
}

function renderParagraph(paragraphIndex: number): void {
  const element = paragraphElements[paragraphIndex];
  const paragraph = props.item.body[paragraphIndex];
  if (!element || !paragraph) {
    return;
  }
  const nodes: Node[] = paragraph.segments.map((segment) =>
    segment.kind === "text" ? document.createTextNode(segment.text) : createAtomElement(segment),
  );
  element.replaceChildren(...nodes, createTrailingBreak());
  refreshAtomIndexes(element, paragraphIndex, paragraph.segments);
  renderedKeys[paragraphIndex] = segmentsKey(paragraph.segments);
}

function syncParagraphs(): void {
  const itemChanged = renderedItemId !== props.item.item_id;
  renderedItemId = props.item.item_id;
  if (itemChanged) {
    closePopover(false);
    statusMessage.value = null;
  }
  renderedKeys.length = props.item.body.length;
  props.item.body.forEach((paragraph, paragraphIndex) => {
    if (itemChanged || renderedKeys[paragraphIndex] !== segmentsKey(paragraph.segments)) {
      renderParagraph(paragraphIndex);
    }
  });
}

function refreshChips(): void {
  editorRoot.value
    ?.querySelectorAll<HTMLElement>(`[${ATOM_ATTRIBUTE}="gap"]`)
    .forEach(applyChipState);
}

onMounted(syncParagraphs);
watch(() => [props.item.item_id, props.item.body] as const, syncParagraphs, { flush: "post" });
watch(() => props.item.gaps, refreshChips, { deep: true, flush: "post" });

function handleParagraphInput(paragraphIndex: number): void {
  const element = paragraphElements[paragraphIndex];
  const paragraph = props.item.body[paragraphIndex];
  if (!element || !paragraph) {
    return;
  }
  const segments = segmentsFromParts(partsFromParagraphElement(element));
  if (!sameAtomSequence(segments, paragraph.segments)) {
    renderParagraph(paragraphIndex);
    statusMessage.value = ATOM_GUARD_COPY;
    return;
  }
  if (segments.length === 0) {
    statusMessage.value = EMPTY_PARAGRAPH_COPY;
    return;
  }
  statusMessage.value = null;
  ensureTrailingBreak(element);
  refreshAtomIndexes(element, paragraphIndex, segments);
  const key = segmentsKey(segments);
  if (key === renderedKeys[paragraphIndex]) {
    return;
  }
  renderedKeys[paragraphIndex] = key;
  emit("updateParagraphSegments", props.item.item_id, paragraphIndex, segments);
}

function handleParagraphFocusOut(paragraphIndex: number): void {
  const element = paragraphElements[paragraphIndex];
  if (!element) {
    return;
  }
  // An emptied paragraph was never emitted; restore the saved text.
  if (segmentsFromParts(partsFromParagraphElement(element)).length === 0) {
    renderParagraph(paragraphIndex);
    statusMessage.value = null;
  }
}

function atomElementsIn(element: HTMLElement): HTMLElement[] {
  return Array.from(element.querySelectorAll<HTMLElement>(`[${ATOM_ATTRIBUTE}]`));
}

function isAtomNode(node: Node | null): boolean {
  return node instanceof HTMLElement && node.hasAttribute(ATOM_ATTRIBUTE);
}

function isEmptyTextNode(node: Node | null): boolean {
  return node !== null && node.nodeType === Node.TEXT_NODE && (node.textContent ?? "").length === 0;
}

/** Whether a collapsed caret sits directly beside an atom in the delete direction. */
function caretBesideAtom(
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

function liveRangesFor(event: InputEvent): Range[] {
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
  if (ranges.length > 0) {
    return ranges;
  }
  return selectionRanges();
}

function selectionRanges(): Range[] {
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

function rangesTouchAtom(root: HTMLElement, ranges: Range[], inputType: string | null): boolean {
  const atoms = atomElementsIn(root);
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

function insertPlainText(paragraphIndex: number, text: string): void {
  const element = paragraphElements[paragraphIndex];
  const range = selectionRanges()[0];
  if (!element || !range || !element.contains(range.commonAncestorContainer)) {
    return;
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
  handleParagraphInput(paragraphIndex);
}

function handleBeforeInput(paragraphIndex: number, event: InputEvent): void {
  const element = paragraphElements[paragraphIndex];
  if (!element) {
    return;
  }
  if (props.disabled) {
    event.preventDefault();
    return;
  }
  const inputType = event.inputType;
  if (inputType.startsWith("history")) {
    // Undo/redo pass through; the atom-sequence check in `input` restores any atom.
    return;
  }
  if (rangesTouchAtom(element, liveRangesFor(event), inputType)) {
    event.preventDefault();
    statusMessage.value = ATOM_GUARD_COPY;
    return;
  }
  if (inputType === "insertParagraph" || inputType === "insertLineBreak") {
    event.preventDefault();
    insertPlainText(paragraphIndex, "\n");
  }
}

function handlePaste(paragraphIndex: number, event: ClipboardEvent): void {
  event.preventDefault();
  const element = paragraphElements[paragraphIndex];
  if (!element || props.disabled) {
    return;
  }
  if (rangesTouchAtom(element, selectionRanges(), null)) {
    statusMessage.value = ATOM_GUARD_COPY;
    return;
  }
  const text = event.clipboardData?.getData("text/plain") ?? "";
  if (text.length > 0) {
    insertPlainText(paragraphIndex, text.replace(/\r\n?/g, "\n"));
  }
}

function chipFromEvent(event: Event): HTMLElement | null {
  const target = event.target;
  if (!(target instanceof Element)) {
    return null;
  }
  return target.closest<HTMLElement>(`[${ATOM_ATTRIBUTE}="gap"]`);
}

function handleDragStart(event: DragEvent): void {
  const target = event.target;
  if (target instanceof Element && target.closest(`[${ATOM_ATTRIBUTE}]`)) {
    event.preventDefault();
  }
}

function handleParagraphClick(event: MouseEvent): void {
  const chip = chipFromEvent(event);
  if (chip) {
    event.preventDefault();
    openPopover(chip);
  }
}

function handleParagraphKeydown(event: KeyboardEvent): void {
  const chip = chipFromEvent(event);
  if (chip && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    openPopover(chip);
  }
}

function openPopover(chip: HTMLElement): void {
  if (props.disabled) {
    return;
  }
  const gapId = chip.getAttribute("data-gap-id");
  const root = editorRoot.value;
  if (!gapId || !root) {
    return;
  }
  openChip?.setAttribute("aria-expanded", "false");
  const chipRect = chip.getBoundingClientRect();
  const rootRect = root.getBoundingClientRect();
  openChip = chip;
  chip.setAttribute("aria-expanded", "true");
  openGap.value = {
    gapId,
    top: chipRect.bottom - rootRect.top + 4,
    // Keep the 18rem popover inside the editor when the chip sits near the right edge.
    left: Math.max(0, Math.min(chipRect.left - rootRect.left, rootRect.width - 288)),
  };
  void nextTick(() => {
    popoverInput.value?.focus();
    popoverInput.value?.select();
  });
}

function closePopover(returnFocus: boolean): void {
  const chip = openChip;
  openChip = null;
  openGap.value = null;
  chip?.setAttribute("aria-expanded", "false");
  if (returnFocus && chip?.isConnected) {
    chip.focus();
  }
}

function handleGapValuesChange(gapId: string, event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("updateGapValues", props.item.item_id, gapId, parseAcceptedValues(input.value));
}

function handlePopoverKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    // Discard the uncommitted text so leaving the input does not commit it.
    const input = event.target as HTMLInputElement;
    input.value = openGapModel.value?.accepted_values.join(", ") ?? "";
    closePopover(true);
  } else if (event.key === "Enter") {
    event.preventDefault();
    // Moving focus to the chip blurs the input, which commits through `change`.
    closePopover(true);
  }
}

function handlePopoverFocusOut(event: FocusEvent): void {
  const next = event.relatedTarget;
  const popover = event.currentTarget as HTMLElement;
  if (next instanceof Node && popover.contains(next)) {
    return;
  }
  closePopover(false);
}
</script>

<template>
  <fieldset
    class="grid gap-3 border border-navy/20 bg-panel p-4"
    data-test="exam-workspace-body-editor"
  >
    <legend class="px-1 text-xs font-semibold text-navy/80">
      Frågetext
    </legend>
    <div
      ref="editorRoot"
      class="relative grid gap-4"
    >
      <div
        v-for="(paragraph, paragraphIndex) in item.body"
        :key="paragraphIndex"
        :ref="(element) => setParagraphElement(paragraphIndex, element)"
        class="min-h-14 whitespace-pre-wrap break-words border border-navy/35 bg-canvas px-4 py-3 text-base leading-loose text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action/40"
        role="textbox"
        aria-multiline="true"
        :aria-label="`Frågetext, stycke ${paragraphIndex + 1}`"
        :aria-disabled="disabled ? 'true' : undefined"
        :contenteditable="disabled ? 'false' : editableMode"
        :data-test="`exam-workspace-body-paragraph-${paragraphIndex}`"
        spellcheck="true"
        lang="sv"
        @beforeinput="handleBeforeInput(paragraphIndex, $event as InputEvent)"
        @input="handleParagraphInput(paragraphIndex)"
        @paste="handlePaste(paragraphIndex, $event)"
        @click="handleParagraphClick"
        @keydown="handleParagraphKeydown"
        @dragstart="handleDragStart"
        @focusout="handleParagraphFocusOut(paragraphIndex)"
      />

      <div
        v-if="openGap"
        class="absolute z-10 grid w-72 max-w-full gap-2 border border-navy bg-panel p-3 shadow-[4px_4px_0_0_rgba(0,0,0,0.15)]"
        :style="{ top: `${openGap.top}px`, left: `${openGap.left}px` }"
        role="dialog"
        :aria-label="`Godkända svar för lucka ${openGapNumber}`"
        data-test="exam-workspace-gap-popover"
        @focusout="handlePopoverFocusOut"
      >
        <label class="grid gap-1 text-xs font-semibold text-navy/80">
          Lucka {{ openGapNumber }} – godkända svar (kommaseparerade)
          <input
            ref="popoverInput"
            class="min-h-10 w-full border border-navy/35 bg-canvas px-3 text-sm font-normal text-navy"
            type="text"
            :value="openGapModel?.accepted_values.join(', ') ?? ''"
            :data-test="`exam-workspace-gap-values-${openGap.gapId}`"
            @change="handleGapValuesChange(openGap.gapId, $event)"
            @keydown="handlePopoverKeydown"
          >
        </label>
        <span
          v-if="openGapModel?.hint"
          class="text-[11px] leading-snug text-navy/65"
        >
          Ledtråd: {{ openGapModel.hint }}
        </span>
      </div>
    </div>

    <p
      v-if="item.kind === 'free_text'"
      class="text-[11px] leading-snug text-navy/65"
    >
      Fritextfråga – eleven svarar med egen text.
    </p>
    <p
      v-if="statusMessage"
      class="text-xs leading-snug text-navy/70"
      role="status"
      aria-live="polite"
      data-test="exam-workspace-body-status"
    >
      {{ statusMessage }}
    </p>
    <p
      v-if="hasPartialGapKey"
      class="text-xs leading-snug text-navy/70"
      role="status"
      aria-live="polite"
      data-test="exam-workspace-gap-key-hint"
    >
      {{ PARTIAL_GAP_KEY_GUIDANCE }}
    </p>
  </fieldset>
</template>
