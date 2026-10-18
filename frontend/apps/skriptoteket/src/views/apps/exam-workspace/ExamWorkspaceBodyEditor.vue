<script setup lang="ts">
/**
 * Exam workspace question-text editor.
 *
 * Domain purpose:
 *   Let the teacher edit a question's text as one document in the shared
 *   rich-text editor: the five kept marks, a heading level, every gap shown as
 *   an inline chip and every image as a fixed atom. The toolbar toggles the
 *   marks and heading level of the one active rich surface — this question
 *   text or a choice option / Kategorisera entry — and Ctrl/Cmd+B, I and U
 *   toggle marks from the keyboard. Activating a gap chip opens a small
 *   popover where the teacher edits that gap's accepted answers, removes an
 *   automatic answer the conversion added, or replaces the whole gap with its
 *   first accepted answer as plain text ("Visa som text").
 *
 *   A selection that covers a gap or a picture deletes it like any other
 *   character, without confirmation: the body edit drops the gap's record and
 *   an unreferenced picture's asset, and Ångra (Ctrl/Cmd+Z included) brings
 *   text, record and asset back. Paste and drop never carry a gap or picture.
 *   While `disabled` is set, nothing can be edited, an open popover closes
 *   without committing, and no gap change is forwarded.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for the selected item.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state
 *     (`updateItemBody`, `updateItemGapValues`).
 *   - `ExamWorkspaceRichTextEditor` owns the text, marks and atoms,
 *     `ExamWorkspaceMarkToolbar` the glyph buttons, and
 *     `ExamWorkspaceGapPopover` edits one gap's accepted answers.
 *   - `examWorkspaceRichTextTarget` is the shared active target the toolbar
 *     reads and calls, so a glyph action always edits the surface that owns
 *     the selection, never a stale one.
 */

import { computed, ref, useId, watch } from "vue";

import type { NativeExamBodyParagraph, NativeExamChoice, NativeExamItem } from "../../../api/examWorkspace";
import {
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { examGapStates, gapNumberIn } from "./examWorkspaceGapLabels";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { useRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";

type HeadingLevel = 1 | 2 | 3;

const POPOVER_WIDTH_PX = 448;

const props = defineProps<{
  item: NativeExamItem;
  disabled?: boolean;
  /** Asset URL per asset id; a mapped picture renders, an unmapped one keeps its placeholder. */
  assetUrls?: Record<string, string>;
}>();

const emit = defineEmits<{
  updateBody: [itemId: string, body: NativeExamBodyParagraph[], structural: boolean];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updateGapOptions: [itemId: string, gapId: string, options: NativeExamChoice[], correctOptionId: string | null];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
}>();

type OpenGap = {
  itemId: string;
  gapId: string;
  top: number;
  left: number;
};

const labelId = useId();
const editorRoot = ref<HTMLElement | null>(null);
const editor = ref<InstanceType<typeof ExamWorkspaceRichTextEditor> | null>(null);
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

/** How each gap of the item reads in the text: its accepted answers, or "Lucka N" while it has none. */
const gapStates = computed(() => examGapStates(props.item.gaps));

function handleToggleMark(mark: BodyMark): void {
  activeRichTextTarget.value?.toggleMark(mark);
}

function handleToggleHeading(level: HeadingLevel): void {
  activeRichTextTarget.value?.toggleHeading(level);
}

function openPopover(gapId: string, chip: HTMLElement): void {
  if (props.disabled) {
    return;
  }
  const root = editorRoot.value;
  if (!root) {
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
    // The text surface takes focus back with its selection (the gap) intact.
    chip.closest<HTMLElement>("[contenteditable='true']")?.focus();
  }
}

function handleGapCommit(itemId: string, gapId: string, acceptedValues: string[]): void {
  if (props.disabled) {
    return;
  }
  emit("updateGapValues", itemId, gapId, acceptedValues);
}

function handleGapOptions(
  itemId: string,
  gapId: string,
  options: NativeExamChoice[],
  correctOptionId: string | null,
): void {
  if (props.disabled) {
    return;
  }
  emit("updateGapOptions", itemId, gapId, options, correctOptionId);
}

function handleGapAutomaticValueRemoval(itemId: string, gapId: string, value: string): void {
  if (props.disabled) {
    return;
  }
  emit("removeAutomaticValue", itemId, gapId, value);
}

/** The chip this action removes cannot keep focus, so the text takes it. */
function handleGapAsText(itemId: string, gapId: string): void {
  if (props.disabled) {
    return;
  }
  closePopover(false);
  emit("showGapAsText", itemId, gapId);
  editor.value?.focus();
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
        <ExamWorkspaceRichTextEditor
          ref="editor"
          :body="item.body"
          label="Frågetext"
          test-id="exam-workspace-body-editor-surface"
          variant="field"
          :disabled="disabled"
          :gap-states="gapStates"
          :asset-urls="assetUrls"
          gaps-interactive
          @activate-gap="openPopover"
          @update="(body, structural) => emit('updateBody', item.item_id, body, structural)"
        />

        <ExamWorkspaceGapPopover
          v-if="openGap"
          :key="`${openGap.itemId}:${openGap.gapId}`"
          :item-id="openGap.itemId"
          :gap-id="openGap.gapId"
          :gap-number="openGapNumber"
          :gap="openGapModel"
          :dropdown="item.kind === 'inline_choice'"
          :top="openGap.top"
          :left="openGap.left"
          @commit="handleGapCommit"
          @update-options="handleGapOptions"
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
