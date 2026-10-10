<script setup lang="ts">
/**
 * Exam workspace question-text editor.
 *
 * Domain purpose:
 *   Let the teacher edit each paragraph of a question as one continuous
 *   text, with every gap shown as an inline chip and every image as a fixed
 *   "Bild" marker. Activating a gap chip opens a small popover where the
 *   teacher edits that gap's accepted answers. Gaps and images are the
 *   Exam.net contract, so typing, pasting, cutting, dragging, dropping or
 *   undo can never remove, add or reorder them. While `disabled` is set,
 *   nothing can be edited and an open popover closes without committing.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceItemEditor` for the selected item.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state
 *     (`updateItemParagraphSegments`, `updateItemGapValues`).
 *   - Paragraph DOM is built imperatively from the model so the caret stays
 *     put while the teacher types; `examWorkspaceBodySegments` converts
 *     between that DOM and model segments, and `examWorkspaceBodyCaret`
 *     guards edits that would touch an atom.
 *   - `ExamWorkspaceGapPopover` edits one gap's accepted answers.
 */

import { computed, onMounted, ref, watch } from "vue";
import type { ComponentPublicInstance } from "vue";

import type { NativeExamItem, NativeExamBodySegment } from "../../../api/examWorkspace";
import {
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";
import {
  insertPlainText,
  liveRangesFor,
  rangesTouchAtom,
  type TouchedAtomKind,
  selectionRanges,
} from "./examWorkspaceBodyCaret";
import {
  applyChipState,
  ATOM_ATTRIBUTE,
  ensureTrailingBreak,
  gapNumberIn,
  partsFromParagraphElement,
  refreshAtomIndexes,
  renderParagraphElement,
  sameAtomSequence,
  segmentsFromParts,
  segmentsKey,
} from "./examWorkspaceBodySegments";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";

const ATOM_GUARD_COPY = "Luckor och bilder kan inte tas bort i texten.";
const DELETE_NEXT_TO_GAP_COPY =
  "Luckan tas inte bort med Backsteg eller Delete. Öppna luckan för att ändra svaret.";
const DELETE_NEXT_TO_IMAGE_COPY = "Bilden tas inte bort i texten.";
const EMPTY_PARAGRAPH_COPY = "Stycket måste innehålla text.";
const POPOVER_WIDTH_PX = 448;

function atomGuardCopy(inputType: string, atom: TouchedAtomKind): string {
  if (inputType !== "deleteContentBackward" && inputType !== "deleteContentForward") {
    return ATOM_GUARD_COPY;
  }
  if (atom === "gap") {
    return DELETE_NEXT_TO_GAP_COPY;
  }
  return atom === "asset" ? DELETE_NEXT_TO_IMAGE_COPY : ATOM_GUARD_COPY;
}

const props = defineProps<{
  item: NativeExamItem;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  updateParagraphSegments: [itemId: string, paragraphIndex: number, segments: NativeExamBodySegment[]];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
}>();

type OpenGap = { itemId: string; gapId: string; top: number; left: number };

const editableMode = detectEditableMode();
const editorRoot = ref<HTMLElement | null>(null);
const statusMessage = ref<string | null>(null);
const openGap = ref<OpenGap | null>(null);

const hasPartialGapKey = computed(() => isPartiallyKeyedGapItem(props.item));
const openGapModel = computed(() =>
  openGap.value === null
    ? null
    : (props.item.gaps.find((gap) => gap.gap_id === openGap.value?.gapId) ?? null),
);
const openGapNumber = computed(() =>
  openGap.value === null ? 0 : gapNumberIn(props.item.gaps, openGap.value.gapId),
);

// Imperative paragraph state; deliberately not reactive.
const paragraphElements: (HTMLElement | null)[] = [];
const renderedKeys: (string | undefined)[] = [];
let renderedItemId: string | null = null;
let openChip: HTMLElement | null = null;
let composingIndex: number | null = null;

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

function renderParagraph(paragraphIndex: number): void {
  const element = paragraphElements[paragraphIndex];
  const paragraph = props.item.body[paragraphIndex];
  if (!element || !paragraph) {
    return;
  }
  renderParagraphElement(element, paragraph.segments, props.item.gaps);
  refreshAtomIndexes(element, paragraphIndex, paragraph.segments);
  renderedKeys[paragraphIndex] = segmentsKey(paragraph.segments);
}

function syncParagraphs(): void {
  const itemChanged = renderedItemId !== props.item.item_id;
  renderedItemId = props.item.item_id;
  if (itemChanged) {
    closePopover(false);
    statusMessage.value = null;
    composingIndex = null;
  }
  renderedKeys.length = props.item.body.length;
  props.item.body.forEach((paragraph, paragraphIndex) => {
    if (paragraphIndex === composingIndex) {
      // Rebuilding under an active IME composition would break it.
      return;
    }
    if (itemChanged || renderedKeys[paragraphIndex] !== segmentsKey(paragraph.segments)) {
      renderParagraph(paragraphIndex);
    }
  });
}

function refreshChips(): void {
  editorRoot.value
    ?.querySelectorAll<HTMLElement>(`[${ATOM_ATTRIBUTE}="gap"]`)
    .forEach((chip) => applyChipState(chip, props.item.gaps));
}

onMounted(syncParagraphs);
watch(() => [props.item.item_id, props.item.body] as const, syncParagraphs, { flush: "post" });
watch(() => props.item.gaps, refreshChips, { deep: true, flush: "post" });
watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) {
      closePopover(false);
    }
  },
);

function handleParagraphInput(paragraphIndex: number, event?: Event): void {
  if (paragraphIndex === composingIndex || (event instanceof InputEvent && event.isComposing)) {
    // Serialized on `compositionend`.
    return;
  }
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

function handleCompositionStart(paragraphIndex: number): void {
  composingIndex = paragraphIndex;
}

function handleCompositionEnd(paragraphIndex: number): void {
  composingIndex = null;
  handleParagraphInput(paragraphIndex);
}

function handleParagraphFocusOut(paragraphIndex: number): void {
  const element = paragraphElements[paragraphIndex];
  if (!element || paragraphIndex === composingIndex) {
    return;
  }
  // An emptied paragraph was never emitted; restore the saved text.
  if (segmentsFromParts(partsFromParagraphElement(element)).length === 0) {
    renderParagraph(paragraphIndex);
    statusMessage.value = null;
  }
}

function insertTextAtCaret(paragraphIndex: number, text: string): void {
  const element = paragraphElements[paragraphIndex];
  if (element && insertPlainText(element, text)) {
    handleParagraphInput(paragraphIndex);
  }
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
  const touchedAtom = rangesTouchAtom(element, liveRangesFor(event), inputType);
  if (touchedAtom !== null) {
    event.preventDefault();
    statusMessage.value = atomGuardCopy(inputType, touchedAtom);
    return;
  }
  if (inputType === "insertParagraph" || inputType === "insertLineBreak") {
    event.preventDefault();
    insertTextAtCaret(paragraphIndex, "\n");
  }
}

function handlePaste(paragraphIndex: number, event: ClipboardEvent): void {
  event.preventDefault();
  const element = paragraphElements[paragraphIndex];
  if (!element || props.disabled) {
    return;
  }
  if (rangesTouchAtom(element, selectionRanges(), null) !== null) {
    statusMessage.value = ATOM_GUARD_COPY;
    return;
  }
  const text = event.clipboardData?.getData("text/plain") ?? "";
  if (text.length > 0) {
    insertTextAtCaret(paragraphIndex, text.replace(/\r\n?/g, "\n"));
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
    itemId: props.item.item_id,
    gapId,
    top: chipRect.bottom - rootRect.top + 4,
    // Keep the popover inside the editor when the chip sits near the right edge.
    left: Math.max(0, Math.min(chipRect.left - rootRect.left, rootRect.width - POPOVER_WIDTH_PX)),
  };
}

function closePopover(returnFocus: boolean): void {
  if (openGap.value === null) {
    return;
  }
  const chip = openChip;
  openChip = null;
  openGap.value = null;
  chip?.setAttribute("aria-expanded", "false");
  if (returnFocus && chip?.isConnected) {
    chip.focus();
  }
}

function handleGapCommit(itemId: string, gapId: string, acceptedValues: string[]): void {
  if (props.disabled) {
    return;
  }
  emit("updateGapValues", itemId, gapId, acceptedValues);
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
        @input="handleParagraphInput(paragraphIndex, $event)"
        @compositionstart="handleCompositionStart(paragraphIndex)"
        @compositionend="handleCompositionEnd(paragraphIndex)"
        @paste="handlePaste(paragraphIndex, $event)"
        @click="handleParagraphClick"
        @keydown="handleParagraphKeydown"
        @dragstart="handleDragStart"
        @dragover="handleDragOver"
        @drop.prevent
        @focusout="handleParagraphFocusOut(paragraphIndex)"
      />

      <ExamWorkspaceGapPopover
        v-if="openGap"
        :key="`${openGap.itemId}:${openGap.gapId}`"
        :item-id="openGap.itemId"
        :gap-id="openGap.gapId"
        :gap-number="openGapNumber"
        :gap="openGapModel"
        :top="openGap.top"
        :left="openGap.left"
        @commit="handleGapCommit"
        @close="closePopover"
      />
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

<style scoped>
/* Atom labels are CSS-generated so copied or dragged text never contains them. */
:deep([data-atom][data-label])::before {
  content: attr(data-label);
}
</style>
