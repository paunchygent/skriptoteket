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
 *   first accepted answer as plain text ("Visa som text"). The export-blocker
 *   jump opens a gap the same way through a bubbling open-gap request on its
 *   chip (see `examWorkspaceGapOpenRequest`). A Lucktext or
 *   dropdown-Lucktext question grows its gaps from here: the toolbar's Lucka
 *   button turns the selection, or the word at the caret, into a gap (or
 *   inserts an empty gap), and a click inside a word shows a small floating
 *   "Lucka" button ("Gör till lucka" tooltip and accessible name) that
 *   converts that word. The editor emits the
 *   change as one `createGap`, the owner adds the gap record as one
 *   structural edit, and the new gap's popover opens at once.
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
 *   - `examWorkspaceItemEdits` names the next free gap id (`nextGapId`); the
 *     owner applies the emitted `createGap` through `createItemGap`.
 *   - `examWorkspaceRichTextTarget` is the shared active target the toolbar
 *     reads and calls, so a glyph action always edits the surface that owns
 *     the selection, never a stale one.
 */

import { computed, nextTick, ref, useId, watch } from "vue";

import type { NativeExamBodyParagraph, NativeExamChoice, NativeExamItem } from "../../../api/examWorkspace";
import {
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";
import { examGapStates, gapNumberIn } from "./examWorkspaceGapLabels";
import { nextGapId } from "./examWorkspaceGapEdits";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { useExamWorkspaceRichTextToolbar } from "./useExamWorkspaceRichTextToolbar";

const props = defineProps<{
  item: NativeExamItem;
  disabled?: boolean;
  /** Asset URL per asset id; a mapped picture renders, an unmapped one keeps its placeholder. */
  assetUrls?: Record<string, string>;
}>();

const emit = defineEmits<{
  updateBody: [itemId: string, body: NativeExamBodyParagraph[], structural: boolean];
  createGap: [itemId: string, body: NativeExamBodyParagraph[], gapId: string, seed: string];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updateGapOptions: [itemId: string, gapId: string, options: NativeExamChoice[], correctOptionId: string | null];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
}>();

type OpenGap = {
  itemId: string;
  gapId: string;
  anchor: HTMLElement;
};

const labelId = useId();
const editor = ref<InstanceType<typeof ExamWorkspaceRichTextEditor> | null>(null);
const root = ref<HTMLElement | null>(null);
const openGap = ref<OpenGap | null>(null);
const { activeRichTextTarget, activeMarks, activeHeading, toggleMark, toggleHeading } =
  useExamWorkspaceRichTextToolbar();
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
/** Whether this question kind grows gaps: Lucktext and dropdown-Lucktext. */
const gapKind = computed(() => props.item.kind === "gap_fill" || props.item.kind === "inline_choice");
/** The id the next created gap takes, or null at the gap_999 cap. */
const newGapId = computed(() => (gapKind.value ? nextGapId(props.item) : null));

/** How each gap of the item reads in the text: its accepted answers, or "Lucka N" while it has none. */
const gapStates = computed(() => examGapStates(props.item.gaps));

/** Turn the selection, or the word at the caret, into the next free gap. */
function handleMakeGap(): void {
  const gapId = newGapId.value;
  if (props.disabled || gapId === null) {
    return;
  }
  const target = activeRichTextTarget.value;
  if (target !== null) {
    target.makeGap(gapId);
    return;
  }
  // No surface is active yet: the caret lands at the end of the question
  // text, while the focus — and with it the registration as the active
  // target — lands on the next animation frame (TipTap defers `focus()`),
  // so the gap command runs once this surface owns the toolbar.
  editor.value?.focus();
  requestAnimationFrame(() => {
    if (props.disabled || newGapId.value !== gapId) {
      return;
    }
    if (root.value?.contains(document.activeElement) !== true) {
      return;
    }
    activeRichTextTarget.value?.makeGap(gapId);
  });
}

function openPopover(gapId: string, chip: HTMLElement): void {
  if (props.disabled) {
    return;
  }
  openChip?.setAttribute("aria-expanded", "false");
  openChip = chip;
  chip.setAttribute("aria-expanded", "true");
  // The popover anchors itself to the chip from its viewport rect.
  openGap.value = {
    itemId: props.item.item_id,
    gapId,
    anchor: chip,
  };
}

/**
 * Open the popover for the chip an open-gap request bubbled from (the event
 * mirrors EXAM_WORKSPACE_OPEN_GAP_EVENT in `examWorkspaceGapOpenRequest`);
 * anything without a gap id opens nothing.
 */
function handleOpenGapRequest(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const chip = target.closest("[data-gap-id]");
  if (!(chip instanceof HTMLElement) || root.value?.contains(chip) !== true) {
    return;
  }
  const gapId = chip.getAttribute("data-gap-id");
  if (gapId === null) {
    return;
  }
  openPopover(gapId, chip);
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

/** Forward one gap creation and open the new gap's popover at its chip. */
function handleCreateGap(body: NativeExamBodyParagraph[], gapId: string, seed: string): void {
  if (props.disabled) {
    return;
  }
  emit("createGap", props.item.item_id, body, gapId, seed);
  void nextTick(() => {
    // The owner writes the emitted body back, so the editor keeps its
    // content and the new chip is already in this surface.
    const chip = root.value?.querySelector<HTMLElement>(`[data-gap-id="${gapId}"]`);
    if (chip) {
      openPopover(gapId, chip);
    }
  });
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
    ref="root"
    class="mb-4 grid gap-1.5"
    role="group"
    :aria-labelledby="labelId"
    data-test="exam-workspace-body-editor"
    @exam-workspace-open-gap="handleOpenGapRequest"
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
        :show-gap="gapKind"
        :gap-disabled-reason="gapKind && newGapId === null ? 'Högst 999 luckor' : null"
        @toggle-mark="toggleMark"
        @toggle-heading="toggleHeading"
        @make-gap="handleMakeGap"
      />
      <div class="xw-rich__body grid gap-2">
        <ExamWorkspaceRichTextEditor
          :key="item.item_id"
          ref="editor"
          :body="item.body"
          label="Frågetext"
          test-id="exam-workspace-body-editor-surface"
          variant="field"
          :disabled="disabled"
          :gap-states="gapStates"
          :asset-urls="assetUrls"
          gaps-interactive
          :next-gap-id="gapKind ? newGapId : undefined"
          @activate-gap="openPopover"
          @create-gap="handleCreateGap"
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
          :anchor="openGap.anchor"
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
