<script setup lang="ts">
/**
 * Exam workspace rich paragraph.
 *
 * Domain purpose:
 *   One paragraph of a rich body as one continuous editable text: text with
 *   its five marks, every gap shown as an inline chip and every image as a
 *   fixed atom that renders the actual picture once its asset URL is known.
 *   The element is always a real `contenteditable` host — never
 *   `plaintext-only` — because the text carries formatting; the browser's own
 *   `format*` input is intercepted and every rich operation goes through this
 *   component, which never uses the deprecated `execCommand`. Ctrl/Cmd+B, I
 *   and U toggle a mark on the selected range and the toolbar calls the same
 *   toggle. Gaps and images are the Exam.net contract, so typing, pasting,
 *   cutting, dragging, dropping or undo can never remove, add or reorder
 *   them. While `disabled` is set, nothing can be edited and no formatted
 *   edit is forwarded.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceBodyEditor` for question paragraphs and by
 *     `ExamWorkspaceRichTextEntry` for a choice or matching entry.
 *   - `examWorkspaceBodySegments` serializes the DOM to model segments and
 *     back; `examWorkspaceBodyMarks` toggles a mark; `examWorkspaceBodyCaret`
 *     guards edits that would touch an atom; `examWorkspaceBodySelection`
 *     keeps the caret across a mark rebuild.
 */

import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamGap,
} from "../../../api/examWorkspace";
import {
  insertPlainText,
  liveRangesFor,
  rangesTouchAtom,
  selectionRanges,
  type TouchedAtomKind,
} from "./examWorkspaceBodyCaret";
import { marksForOffsets, withToggledMark } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import {
  applyAssetState,
  applyChipState,
  ATOM_ATTRIBUTE,
  ensureTrailingBreak,
  partsFromParagraphElement,
  refreshAtomIndexes,
  renderParagraphElement,
  renderParagraphParts,
  sameAtomSequence,
  segmentsFromParts,
  segmentsKey,
} from "./examWorkspaceBodySegments";
import {
  rangeFromOffsets,
  selectionOffsets,
  type ParagraphSelection,
} from "./examWorkspaceBodySelection";

const ATOM_GUARD_COPY = "Luckor och bilder kan inte tas bort i texten.";
const DELETE_NEXT_TO_GAP_COPY =
  "Luckan tas inte bort med Backsteg eller Delete. Öppna luckan för att ändra svaret.";
const DELETE_NEXT_TO_IMAGE_COPY = "Bilden kan inte tas bort i texten.";
const EMPTY_PARAGRAPH_COPY = "Stycket måste innehålla text.";

function atomGuardCopy(inputType: string, atom: TouchedAtomKind): string {
  if (inputType !== "deleteContentBackward" && inputType !== "deleteContentForward") {
    return ATOM_GUARD_COPY;
  }
  if (atom === "gap") {
    return DELETE_NEXT_TO_GAP_COPY;
  }
  return atom === "asset" ? DELETE_NEXT_TO_IMAGE_COPY : ATOM_GUARD_COPY;
}

function shortcutMark(key: string): BodyMark | null {
  const lower = key.toLowerCase();
  if (lower === "b") {
    return "bold";
  }
  if (lower === "i") {
    return "italic";
  }
  return lower === "u" ? "underline" : null;
}

function formatMark(inputType: string): BodyMark | null {
  if (inputType === "formatBold") {
    return "bold";
  }
  if (inputType === "formatItalic") {
    return "italic";
  }
  return inputType === "formatUnderline" ? "underline" : null;
}

const props = withDefaults(
  defineProps<{
    paragraph: NativeExamBodyParagraph;
    paragraphIndex: number;
    gaps: NativeExamGap[];
    assetUrls?: Record<string, string>;
    disabled?: boolean;
    label: string;
    testId?: string;
    /** `input` renders the compact single-line surface a choice or matching entry needs. */
    variant?: "paragraph" | "input";
    /** The paragraph's border colour, so an empty or correct choice can mark itself. */
    borderClass?: string;
    /** Gaps and pictures inside a choice or matching entry render without the popover contract. */
    interactiveGaps?: boolean;
  }>(),
  {
    assetUrls: undefined,
    disabled: false,
    testId: undefined,
    variant: "paragraph",
    borderClass: "border-navy/35",
    interactiveGaps: true,
  },
);

const emit = defineEmits<{
  updateSegments: [segments: NativeExamBodySegment[]];
  activateGap: [chip: HTMLElement];
  status: [message: string | null];
  focusParagraph: [];
  selectionMarks: [marks: BodyMark[]];
}>();

const elementRef = ref<HTMLElement | null>(null);
const composing = ref(false);
const renderedKey = ref<string | undefined>(undefined);
let savedOffsets: ParagraphSelection | null = null;

const PARAGRAPH_CLASS =
  "min-h-14 whitespace-pre-wrap [overflow-wrap:anywhere] border bg-canvas px-4 py-3 leading-loose text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action/40";
const INPUT_CLASS =
  "min-h-10 w-full whitespace-pre-wrap [overflow-wrap:anywhere] border bg-panel px-2 py-1.5 leading-normal text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action/40";

const paragraphClass = computed(() => {
  const level = props.paragraph.heading_level;
  const size =
    level === 1
      ? "text-2xl font-semibold"
      : level === 2
        ? "text-xl font-semibold"
        : level === 3
          ? "text-lg font-semibold"
          : "text-base";
  return [props.variant === "input" ? INPUT_CLASS : PARAGRAPH_CLASS, props.borderClass, size];
});

function renderNow(): void {
  const element = elementRef.value;
  if (!element) {
    return;
  }
  renderParagraphElement(
    element,
    props.paragraph.segments,
    props.gaps,
    props.assetUrls,
    props.interactiveGaps,
  );
  refreshAtomIndexes(element, props.paragraphIndex, props.paragraph.segments);
  renderedKey.value = segmentsKey(props.paragraph.segments);
}

function refreshChips(): void {
  elementRef.value
    ?.querySelectorAll<HTMLElement>(`[${ATOM_ATTRIBUTE}="gap"]`)
    .forEach((chip) => applyChipState(chip, props.gaps));
}

/** Update live image atoms in place so an arriving or changed URL never rebuilds the paragraph. */
function refreshAssets(): void {
  elementRef.value
    ?.querySelectorAll<HTMLElement>(`[${ATOM_ATTRIBUTE}="asset"]`)
    .forEach((atom) => {
      const assetId = atom.getAttribute("data-asset-id");
      if (assetId) {
        applyAssetState(atom, assetId, props.assetUrls);
      }
    });
}

onMounted(() => {
  document.addEventListener("selectionchange", rememberSelection);
  renderNow();
});

onBeforeUnmount(() => {
  document.removeEventListener("selectionchange", rememberSelection);
});

watch(
  () => props.paragraph,
  () => {
    if (composing.value) {
      return;
    }
    if (segmentsKey(props.paragraph.segments) !== renderedKey.value) {
      renderNow();
    }
  },
  { flush: "post" },
);
watch(() => props.gaps, refreshChips, { deep: true, flush: "post" });
watch(() => props.assetUrls, refreshAssets, { deep: true, flush: "post" });

function rememberSelection(): void {
  const element = elementRef.value;
  if (!element) {
    return;
  }
  const offsets = selectionOffsets(element);
  if (!offsets) {
    return;
  }
  savedOffsets = offsets;
  emit(
    "selectionMarks",
    marksForOffsets(partsFromParagraphElement(element), offsets.start, offsets.end),
  );
}

function restoreSelection(offsets: ParagraphSelection): void {
  const element = elementRef.value;
  if (!element) {
    return;
  }
  const range = rangeFromOffsets(element, offsets);
  if (!range) {
    return;
  }
  element.focus({ preventScroll: true });
  const selection = window.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
  savedOffsets = offsets;
  emit(
    "selectionMarks",
    marksForOffsets(partsFromParagraphElement(element), offsets.start, offsets.end),
  );
}

/** Add or remove one mark on the selected range, keeping the selection in place. */
function toggleMark(mark: BodyMark): void {
  const element = elementRef.value;
  if (!element || props.disabled) {
    return;
  }
  const offsets = selectionOffsets(element) ?? savedOffsets;
  if (!offsets) {
    return;
  }
  const parts = partsFromParagraphElement(element);
  const next = withToggledMark(parts, offsets.start, offsets.end, mark);
  if (!next) {
    emit("selectionMarks", marksForOffsets(parts, offsets.start, offsets.end));
    return;
  }
  renderParagraphParts(element, next, props.gaps, props.assetUrls, props.interactiveGaps);
  const segments = segmentsFromParts(next);
  refreshAtomIndexes(element, props.paragraphIndex, segments);
  renderedKey.value = segmentsKey(segments);
  emit("status", null);
  emit("updateSegments", segments);
  restoreSelection(offsets);
}

function focus(): void {
  elementRef.value?.focus();
}

defineExpose({ focus, toggleMark });

function handleInput(event?: Event): void {
  if (props.disabled) {
    return;
  }
  if (composing.value || (event instanceof InputEvent && event.isComposing)) {
    // Serialized on `compositionend`.
    return;
  }
  const element = elementRef.value;
  if (!element) {
    return;
  }
  const segments = segmentsFromParts(partsFromParagraphElement(element));
  if (!sameAtomSequence(segments, props.paragraph.segments)) {
    renderNow();
    emit("status", ATOM_GUARD_COPY);
    return;
  }
  if (segments.length === 0) {
    emit("status", EMPTY_PARAGRAPH_COPY);
    return;
  }
  emit("status", null);
  ensureTrailingBreak(element);
  refreshAtomIndexes(element, props.paragraphIndex, segments);
  const key = segmentsKey(segments);
  if (key === renderedKey.value) {
    return;
  }
  renderedKey.value = key;
  emit("updateSegments", segments);
}

function handleCompositionStart(): void {
  composing.value = true;
}

function handleCompositionEnd(): void {
  composing.value = false;
  handleInput();
}

function handleFocusOut(): void {
  const element = elementRef.value;
  if (!element || composing.value) {
    return;
  }
  // An emptied paragraph was never emitted; restore the saved text.
  if (segmentsFromParts(partsFromParagraphElement(element)).length === 0) {
    renderNow();
    emit("status", null);
  }
}

function insertTextAtCaret(text: string): void {
  const element = elementRef.value;
  if (element && insertPlainText(element, text)) {
    handleInput();
  }
}

function handleBeforeInput(event: InputEvent): void {
  const element = elementRef.value;
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
  const touchedAtom = rangesTouchAtom(element, liveRangesFor(event), inputType);
  if (touchedAtom !== null) {
    event.preventDefault();
    emit("status", atomGuardCopy(inputType, touchedAtom));
    return;
  }
  const mark = formatMark(inputType);
  if (mark) {
    event.preventDefault();
    toggleMark(mark);
    return;
  }
  if (inputType === "insertParagraph" || inputType === "insertLineBreak") {
    event.preventDefault();
    insertTextAtCaret("\n");
  }
}

function handlePaste(event: ClipboardEvent): void {
  event.preventDefault();
  const element = elementRef.value;
  if (!element || props.disabled) {
    return;
  }
  if (rangesTouchAtom(element, selectionRanges(), null) !== null) {
    emit("status", ATOM_GUARD_COPY);
    return;
  }
  const text = event.clipboardData?.getData("text/plain") ?? "";
  if (text.length > 0) {
    insertTextAtCaret(text.replace(/\r\n?/g, "\n"));
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

/** Refuse drops so dragged HTML, chips or images never enter a paragraph. */
function handleDragOver(event: DragEvent): void {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "none";
  }
}

function handleClick(event: MouseEvent): void {
  const chip = chipFromEvent(event);
  if (chip && props.interactiveGaps) {
    event.preventDefault();
    emit("activateGap", chip);
  }
}

function handleKeydown(event: KeyboardEvent): void {
  const chip = chipFromEvent(event);
  if (chip && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    if (props.interactiveGaps) {
      emit("activateGap", chip);
    }
    return;
  }
  if ((event.ctrlKey || event.metaKey) && !event.altKey) {
    const mark = shortcutMark(event.key);
    if (mark) {
      event.preventDefault();
      toggleMark(mark);
    }
  }
}

function handleFocus(): void {
  emit("focusParagraph");
  rememberSelection();
}

function handleKeyup(): void {
  rememberSelection();
}

function handleMouseup(): void {
  rememberSelection();
}
</script>

<template>
  <div
    ref="elementRef"
    :class="paragraphClass"
    role="textbox"
    aria-multiline="true"
    :aria-label="label"
    :aria-disabled="disabled ? 'true' : undefined"
    :contenteditable="disabled ? 'false' : 'true'"
    :data-test="testId"
    :data-heading-level="paragraph.heading_level ?? undefined"
    spellcheck="true"
    lang="sv"
    @beforeinput="handleBeforeInput($event as InputEvent)"
    @input="handleInput($event)"
    @compositionstart="handleCompositionStart"
    @compositionend="handleCompositionEnd"
    @paste="handlePaste"
    @click="handleClick"
    @keydown="handleKeydown"
    @keyup="handleKeyup"
    @mouseup="handleMouseup"
    @focus="handleFocus"
    @dragstart="handleDragStart"
    @dragover="handleDragOver"
    @drop.prevent
    @focusout="handleFocusOut"
  />
</template>
