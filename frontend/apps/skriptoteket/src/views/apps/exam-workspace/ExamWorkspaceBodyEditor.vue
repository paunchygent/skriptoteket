<script setup lang="ts">
/**
 * Exam workspace question-text editor.
 *
 * Domain purpose:
 *   Let the teacher edit each paragraph of a question as one continuous
 *   rich text: the five kept marks, a heading level, every gap shown as an
 *   inline chip and every image as a fixed atom. The toolbar toggles the
 *   marks and heading level of the one active rich surface — this fieldset's
 *   own paragraph or a choice option / Kategorisera entry — and Ctrl/Cmd+B,
 *   I and U toggle marks from the keyboard. Activating a gap
 *   chip opens a small popover where the teacher edits that gap's accepted
 *   answers, removes an automatic answer the conversion added, or replaces
 *   the whole gap with its first accepted answer as plain text ("Visa som
 *   text"). Gaps and images are the Exam.net contract, so typing, pasting,
 *   cutting, dragging, dropping or undo can never remove, add or reorder
 *   them. While `disabled` is set, nothing can be edited, an open popover
 *   closes without committing, and no gap change is forwarded.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for the selected item.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state
 *     (`updateItemParagraphSegments`, `updateItemParagraphHeading`,
 *     `updateItemGapValues`).
 *   - `ExamWorkspaceBodyParagraph` owns one paragraph's DOM and marks,
 *     `ExamWorkspaceMarkToolbar` the glyph buttons, and
 *     `ExamWorkspaceGapPopover` edits one gap's accepted answers.
 *   - `examWorkspaceRichTextTarget` is the shared active target the toolbar
 *     reads and calls, so a glyph action always edits the surface that owns
 *     the selection, never a stale one.
 */

import { computed, ref, useId, watch } from "vue";
import type { ComponentPublicInstance } from "vue";

import type { NativeExamBodySegment, NativeExamItem } from "../../../api/examWorkspace";
import {
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { gapNumberIn } from "./examWorkspaceBodySegments";
import ExamWorkspaceBodyParagraph from "./ExamWorkspaceBodyParagraph.vue";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import { useRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextSurfaceOwner } from "./useExamWorkspaceRichTextTarget";

type HeadingLevel = 1 | 2 | 3;
type ParagraphInstance = InstanceType<typeof ExamWorkspaceBodyParagraph>;

const POPOVER_WIDTH_PX = 448;

const props = defineProps<{
  item: NativeExamItem;
  disabled?: boolean;
  /** Asset URL per asset id; a mapped picture renders, an unmapped one keeps its placeholder. */
  assetUrls?: Record<string, string>;
}>();

const emit = defineEmits<{
  updateParagraphSegments: [itemId: string, paragraphIndex: number, segments: NativeExamBodySegment[]];
  updateParagraphHeading: [itemId: string, paragraphIndex: number, headingLevel: HeadingLevel | null];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
}>();

type OpenGap = {
  itemId: string;
  gapId: string;
  paragraphIndex: number;
  top: number;
  left: number;
};

const labelId = useId();
const editorRoot = ref<HTMLElement | null>(null);
const statusMessage = ref<string | null>(null);
const openGap = ref<OpenGap | null>(null);
const richTextTargets = useRichTextTargetRegistry();
const activeRichTextTarget = richTextTargets.active;
let openChip: HTMLElement | null = null;

const hasPartialGapKey = computed(() => isPartiallyKeyedGapItem(props.item));
const openGapModel = computed(() =>
  openGap.value === null
    ? null
    : (props.item.gaps.find((gap) => gap.gap_id === openGap.value?.gapId) ?? null),
);
const openGapNumber = computed(() =>
  openGap.value === null ? 0 : gapNumberIn(props.item.gaps, openGap.value.gapId),
);
const activeMarks = computed(() => activeRichTextTarget.value?.marks.value ?? []);
const activeHeading = computed<HeadingLevel | null>(
  () => activeRichTextTarget.value?.headingLevel() ?? null,
);

/** The question text's semantic owner, so its saved toolbar selection follows the selected item. */
const questionOwner = computed<RichTextSurfaceOwner>(() => ({
  itemId: props.item.item_id,
  surface: "question",
  entryId: null,
}));

/** Imperative paragraph refs; deliberately not reactive, so a toolbar click reaches the live component. */
const paragraphRefs: (ParagraphInstance | null)[] = [];

function setParagraphRef(
  paragraphIndex: number,
  element: Element | ComponentPublicInstance | null,
): void {
  paragraphRefs[paragraphIndex] =
    element instanceof Element ? null : (element as unknown as ParagraphInstance | null);
}

function handleToggleMark(mark: BodyMark): void {
  activeRichTextTarget.value?.toggleMark(mark);
}

function handleToggleHeading(level: HeadingLevel): void {
  activeRichTextTarget.value?.toggleHeading(level);
}

function openPopover(paragraphIndex: number, chip: HTMLElement): void {
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
    paragraphIndex,
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

function handleGapAutomaticValueRemoval(itemId: string, gapId: string, value: string): void {
  if (props.disabled) {
    return;
  }
  emit("removeAutomaticValue", itemId, gapId, value);
}

/** The chip this action removes cannot keep focus, so the paragraph takes it. */
function handleGapAsText(itemId: string, gapId: string): void {
  if (props.disabled) {
    return;
  }
  const paragraphIndex = openGap.value?.paragraphIndex ?? null;
  closePopover(false);
  emit("showGapAsText", itemId, gapId);
  if (paragraphIndex !== null) {
    paragraphRefs[paragraphIndex]?.focus();
  }
}

watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) {
      closePopover(false);
    }
  },
);
</script>

<template>
  <div
    class="mb-4 grid gap-1.5"
    role="group"
    :aria-labelledby="labelId"
    data-test="exam-workspace-body-editor"
  >
    <div
      :id="labelId"
      class="xw-label"
    >
      Frågetext
    </div>
    <div class="xw-rich">
      <ExamWorkspaceMarkToolbar
        class="xw-rich__bar"
        :active-marks="activeMarks"
        :active-heading="activeHeading"
        :disabled="disabled"
        show-headings
        @toggle-mark="handleToggleMark"
        @toggle-heading="handleToggleHeading"
      />
      <div
        ref="editorRoot"
        class="xw-rich__body relative grid gap-2"
      >
        <ExamWorkspaceBodyParagraph
          v-for="(paragraph, paragraphIndex) in item.body"
          :key="`${item.item_id}:${paragraphIndex}`"
          :ref="(element) => setParagraphRef(paragraphIndex, element)"
          :paragraph="paragraph"
          :paragraph-index="paragraphIndex"
          :owner="questionOwner"
          :gaps="item.gaps"
          :asset-urls="assetUrls"
          :disabled="disabled"
          :label="`Frågetext, stycke ${paragraphIndex + 1}`"
          :test-id="`exam-workspace-body-paragraph-${paragraphIndex}`"
          @activate-gap="(chip) => openPopover(paragraphIndex, chip)"
          @toggle-heading="(level) => emit('updateParagraphHeading', item.item_id, paragraphIndex, level)"
          @status="statusMessage = $event"
          @update-segments="(segments) => emit('updateParagraphSegments', item.item_id, paragraphIndex, segments)"
        />

        <ExamWorkspaceGapPopover
          v-if="openGap"
          :key="`${openGap.itemId}:${openGap.gapId}`"
          :item-id="openGap.itemId"
          :gap-id="openGap.gapId"
          :gap-number="openGapNumber"
          :gap="openGapModel"
          :gap-count="item.gaps.length"
          :top="openGap.top"
          :left="openGap.left"
          @commit="handleGapCommit"
          @remove-automatic-value="handleGapAutomaticValueRemoval"
          @show-gap-as-text="handleGapAsText"
          @close="closePopover"
        />
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
  </div>
</template>

<style scoped>
/* Atom labels are CSS-generated so copied or dragged text never contains them. */
:deep([data-atom][data-label])::before {
  content: attr(data-label);
}
</style>
