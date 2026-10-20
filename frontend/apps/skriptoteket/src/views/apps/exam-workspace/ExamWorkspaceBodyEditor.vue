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
 *   automatic the conversion added, or replaces the whole gap with its
 *   first accepted answer as plain text ("Visa som text"). An empty gap stays
 *   while its question is edited: closing its popover removes nothing. The
 *   selection layer removes empty gaps when the teacher leaves the question.
 *   The export-blocker
 *   jump opens a gap the same way through a bubbling open-gap request on its
 *   chip (see `examWorkspaceGapOpenRequest`). A Lucktext or
 *   dropdown-Lucktext question grows its gaps from here: the toolbar's
 *   Luckverktyg toggle (Ctrl+Alt+G,
 *   Cmd+Option+G on macOS) switches one gap tool per question on: while it
 *   is on, a word click or a drag inside one paragraph becomes a gap at
 *   once with no popover, a gap click reverts the gap instead of opening
 *   its popover, and a kept-word click restores the gap. The tool ends by its
 *   toggle, its shortcut, Escape with no popover open, a move to another
 *   question, or the gap_999 cap. A disabled editor only suspends the tool:
 *   the tool stays on, tool clicks make no gap, and an open popover closes;
 *   when the editor is enabled again the tool is still on. The editor emits the
 *   change as one `createGap`, the owner adds the gap record as one
 *   structural edit, and the new gap's popover opens at once. Tom lucka is the
 *   toolbar's `insertEmptyGap` emit: one empty gap at the caret, or at a
 *   selection's end without deleting text, with the tool on or off, refused
 *   with the shared disabled reason outside gap questions and at the cap; its
 *   popover opens at once even with the tool on.
 *
 *   A selection that covers a gap or a picture deletes it like any other
 *   character, without confirmation: the body edit drops the gap's record and
 *   an unreferenced picture's asset, and Ångra (Ctrl/Cmd+Z included) brings
 *   text, record and asset back. Paste and drop never carry a gap or picture.
 *   While `disabled` is set, nothing can be edited, an open popover closes
 *   without committing, and no gap change is forwarded; the gap tool stays
 *   on through the same suspension.
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
import { GAP_TOOL_AT_CAP_REASON, gapDisabledReason } from "./useExamWorkspaceMakeGap";
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
  updateGapOptions: [itemId: string, gapId: string, options: NativeExamChoice[], correctOptionId: string | null, structural: boolean];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
  /** With the tool on, a gap click reverts it through the owner. */
  revertGap: [itemId: string, gapId: string];
  /** With the tool on, a kept-word click restores its gap through the owner. */
  restoreKeptGap: [itemId: string, keptGapId: string, blockIndex: number];
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
const { activeMarks, activeHeading, toggleMark, toggleHeading } =
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

/** The gap tool: while on, word clicks become gaps at once with no popover. */
const gapToolOn = ref(false);

/** Switch the tool on only while this question can still grow gaps; a disabled editor suspends the tool, so the switch does nothing while disabled. */
function toggleGapTool(): void {
  if (props.disabled) {
    return;
  }
  if (gapToolOn.value) {
    gapToolOn.value = false;
    return;
  }
  if (!gapKind.value || newGapId.value === null) {
    return;
  }
  gapToolOn.value = true;
}

/** Escape closes an open gap popover first and the tool second; never while disabled, when the tool is suspended. */
function handleSurfaceEscape(): void {
  if (props.disabled) {
    return;
  }
  if (openGap.value !== null) {
    closePopover(true);
    return;
  }
  if (gapToolOn.value) {
    gapToolOn.value = false;
  }
}

/** How each gap of the item reads in the text: its answers, or "Lucka N" while it has none. */
const gapStates = computed(() => examGapStates(props.item.gaps, props.item.kind));

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
  // An empty gap stays while its question is edited: closing its popover
  // removes nothing. The selection layer removes empty gaps when the teacher
  // leaves the question.
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
  structural: boolean,
): void {
  if (props.disabled) {
    return;
  }
  emit("updateGapOptions", itemId, gapId, options, correctOptionId, structural);
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

/** With the tool on, a gap click reverts the gap as one structural edit. */
function handleRevertGap(gapId: string): void {
  if (props.disabled) {
    return;
  }
  closePopover(false);
  emit("revertGap", props.item.item_id, gapId);
}

/** With the tool on, a kept-word click restores the clicked kept block. */
function handleRestoreKeptGap(keptGapId: string, blockIndex: number): void {
  if (props.disabled) {
    return;
  }
  emit("restoreKeptGap", props.item.item_id, keptGapId, blockIndex);
}

/** Tom lucka: insert one empty gap at the caret, or refuse silently outside gap questions and at the cap. */
function handleInsertEmptyGap(): void {
  if (props.disabled) {
    return;
  }
  if (props.item.kind !== "gap_fill" && props.item.kind !== "inline_choice") {
    return;
  }
  if (gapDisabledReason(newGapId.value) !== null) {
    return;
  }
  editor.value?.insertEmptyGap();
}

/** Forward one gap creation; a tool-made gap opens no popover, but Tom lucka's empty gap always does. */
function handleCreateGap(body: NativeExamBodyParagraph[], gapId: string, seed: string): void {
  if (props.disabled) {
    return;
  }
  emit("createGap", props.item.item_id, body, gapId, seed);
  if (gapToolOn.value && seed !== "") {
    return;
  }
  void nextTick(() => {
    // The owner writes the emitted body back, so the editor keeps its
    // content and the new chip is already in this surface.
    const chip = root.value?.querySelector<HTMLElement>(`[data-gap-id="${gapId}"]`);
    if (chip) {
      openPopover(gapId, chip);
    }
  });
}

/** A disabled editor suspends the gap tool instead of ending it: the tool stays on while only an open popover closes. */
watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) {
      closePopover(false);
    }
  },
);

watch(
  () => props.item.item_id,
  () => {
    gapToolOn.value = false;
    closePopover(false);
  },
);

watch(newGapId, (gapId) => {
  if (gapId === null) {
    gapToolOn.value = false;
  }
});
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
        :gap-tool-disabled-reason="gapKind && newGapId === null ? GAP_TOOL_AT_CAP_REASON : null"
        :empty-gap-disabled-reason="gapKind ? gapDisabledReason(newGapId) : null"
        :gap-tool-on="gapToolOn"
        @toggle-mark="toggleMark"
        @toggle-heading="toggleHeading"
        @toggle-gap-tool="toggleGapTool"
        @insert-empty-gap="handleInsertEmptyGap"
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
          :gap-tool="gapToolOn"
          @activate-gap="openPopover"
          @create-gap="handleCreateGap"
          @revert-gap="handleRevertGap"
          @restore-kept-gap="handleRestoreKeptGap"
          @toggle-gap-tool="toggleGapTool"
          @escape="handleSurfaceEscape"
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
