<script setup lang="ts">
/**
 * Exam workspace question list column.
 *
 * Domain purpose:
 *   Every question of the open exam in order under "Frågor (N)", with "Ny
 *   uppgift" adding a question or an instruction with deluppgifter after the
 *   selected one, and a footer of two fixed lines: the exam total, which says
 *   in amber when the exam text prints another total (cut with an ellipsis,
 *   the full text in a tooltip), and a slot holding both accept actions,
 *   hidden while there is nothing to accept so nothing moves. Above the rows the exam
 *   instruction is one entry: "Instruktioner" with a short preview when the
 *   exam has one, otherwise a quiet "Lägg till instruktioner"; both open it in
 *   the editor. On a phone the list
 *   opens full screen over the editor from the question strip and closes
 *   with Tillbaka or a choice. "Markera" turns the list into Markera mode: a
 *   standalone question carries a checkbox (an ordering question's is
 *   disabled, G6) and a bar at the top groups the ticked questions into a new
 *   part (G2, G11); a part and a question inside a part carry no checkbox.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; rows are `ExamWorkspaceQuestionRow`,
 *     each told only whether it is selected.
 */

import { computed, nextTick, ref, watch } from "vue";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";
import ExamWorkspaceQuestionRow from "./ExamWorkspaceQuestionRow.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspaceFormatPoints, examWorkspacePointsLine, examWorkspacePointsParts } from "./examWorkspaceTotals";
import { EXAM_INSTRUCTIONS_ENTRY_ID } from "./useExamWorkspaceSelection";

const props = defineProps<{
  entries: ExamWorkspaceListEntry[];
  selectedId: string | null;
  /** The start of the exam instruction's text, or `null` when the exam has none. */
  examInstructionsPreview: string | null;
  questionCount: number;
  total: number;
  /** The exam total the exam text prints, only when it differs from `total`. */
  printedTotal: number | null;
  canAdd: boolean;
  /** The workspace is busy: the accept actions wait like the other list actions. */
  disabled: boolean;
  /** The phone shows the list as a full-screen layer. */
  overlay: boolean;
}>();

const examInstructionsSelected = computed(() => props.selectedId === EXAM_INSTRUCTIONS_ENTRY_ID);
const totalParts = computed(() => examWorkspacePointsParts(props.total, props.printedTotal));
/** The footer line in full, for the tooltip when a long printed note is cut by the ellipsis. */
const totalTitle = computed(() =>
  props.printedTotal === null ? undefined : `Totalt ${examWorkspacePointsLine(props.total, props.printedTotal)}`,
);
const anyPrintedDifference = computed(
  () =>
    props.printedTotal !== null ||
    props.entries.some((entry) => entry.kind === "parent" && entry.printedTotal !== null),
);

const emit = defineEmits<{
  select: [id: string];
  add: [kind: TeacherItemKind | "instruction" | "part"];
  group: [itemIds: string[]];
  acceptExamTotal: [];
  acceptPartTotal: [parentId: string];
  acceptAllTotals: [];
  close: [];
}>();

const rows = ref<HTMLElement | null>(null);
const newTrigger = ref<HTMLButtonElement | null>(null);
const newMenuOpen = ref(false);

/** The Markera mode: the list shows a checkbox per standalone question and a group bar. */
const marking = ref(false);
/** The ticked question ids, which only ever hold standalone questions (G11). */
const marked = ref<Set<string>>(new Set());

/** The ticks in document order, as the group command takes them (G10). */
const markedIds = computed(() =>
  props.entries
    .filter((entry) => entry.kind === "item" && entry.parentId === null && marked.value.has(entry.id))
    .map((entry) => entry.id),
);

function startMarking(): void {
  marked.value = new Set();
  marking.value = true;
}

function cancelMarking(): void {
  marked.value = new Set();
  marking.value = false;
}

function toggleMark(id: string): void {
  if (props.disabled) {
    return;
  }
  const next = new Set(marked.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  marked.value = next;
}

function groupMarked(): void {
  if (markedIds.value.length === 0) {
    return;
  }
  emit("group", markedIds.value);
}

// A successful group turns the ticked questions into a part's children, so no
// tick is a standalone question any more and the mode leaves with them; a
// refused group changes nothing and keeps the ticks for a retry.
watch(markedIds, (ids) => {
  if (marking.value && marked.value.size > 0 && ids.length === 0) {
    cancelMarking();
  }
});

watch(
  () => props.selectedId,
  async (id) => {
    await nextTick();
    const row = Array.from(rows.value?.querySelectorAll<HTMLElement>("[data-entry-id]") ?? []).find(
      (element) => element.dataset.entryId === id,
    );
    row?.scrollIntoView?.({ block: "nearest" });
  },
);
</script>

<template>
  <section
    class="list"
    :class="{ 'list--overlay': overlay }"
    aria-labelledby="exam-workspace-list-title"
    data-test="exam-workspace-question-list"
  >
    <div class="list__head">
      <button
        v-if="overlay"
        type="button"
        class="xw-btn"
        data-test="exam-workspace-list-back"
        @click="emit('close')"
      >
        <UiGlyph
          meaning="back"
          :size="20"
        />Tillbaka
      </button>
      <h2
        id="exam-workspace-list-title"
        class="list__title"
      >
        Frågor ({{ questionCount }})
      </h2>
      <div class="list__head-actions">
        <button
          ref="newTrigger"
          type="button"
          class="xw-btn xw-btn--compact"
          :disabled="!canAdd"
          aria-haspopup="menu"
          :aria-expanded="newMenuOpen"
          data-test="exam-workspace-new"
          @click="newMenuOpen = !newMenuOpen"
        >
          <UiGlyph
            meaning="add"
            :size="16"
          />Ny uppgift
        </button>
      </div>
    </div>
    <div
      class="list__markbar"
      data-test="exam-workspace-marking-bar"
    >
      <button
        type="button"
        class="xw-btn xw-btn--compact xw-btn--primary list__markbar-group"
        :class="{ 'list__markbar-group--idle': !marking }"
        :disabled="disabled || markedIds.length === 0"
        data-test="exam-workspace-group-marked"
        @click="groupMarked"
      >
        Skapa del av markerade ({{ markedIds.length }})
      </button>
      <button
        type="button"
        class="xw-btn xw-btn--compact list__markbar-toggle"
        :disabled="disabled"
        :data-test="marking ? 'exam-workspace-marking-cancel' : 'exam-workspace-marking-start'"
        @click="marking ? cancelMarking() : startMarking()"
      >
        <UiGlyph
          v-if="!marking"
          meaning="checkbox-off"
          :size="16"
        />{{ marking ? "Avbryt" : "Markera" }}
      </button>
    </div>
    <div class="list__scroll">
      <div
        class="list__intro"
        :class="{ 'list__intro--selected': examInstructionsSelected }"
      >
        <button
          v-if="examInstructionsPreview !== null"
          type="button"
          class="list__instructions"
          :aria-current="examInstructionsSelected ? 'true' : undefined"
          data-test="exam-workspace-exam-instructions-entry"
          @click="emit('select', EXAM_INSTRUCTIONS_ENTRY_ID)"
        >
          <span class="list__instructions-title">Instruktioner</span>
          <span class="list__instructions-preview">{{ examInstructionsPreview }}</span>
        </button>
        <button
          v-else
          type="button"
          class="xw-btn xw-btn--compact xw-btn--ghost list__add"
          :aria-current="examInstructionsSelected ? 'true' : undefined"
          data-test="exam-workspace-exam-instructions-add"
          @click="emit('select', EXAM_INSTRUCTIONS_ENTRY_ID)"
        >
          Lägg till instruktioner
        </button>
      </div>
      <div
        ref="rows"
        class="list__rows"
        role="grid"
        aria-labelledby="exam-workspace-list-title"
        aria-keyshortcuts="ArrowUp ArrowDown"
      >
        <ExamWorkspaceQuestionRow
          v-for="entry in entries"
          :key="entry.id"
          :entry="entry"
          :selected="entry.id === selectedId"
          :disabled="disabled"
          :marking="marking"
          :marked="marked.has(entry.id)"
          @select="emit('select', $event)"
          @accept-total="emit('acceptPartTotal', $event)"
          @toggle-mark="toggleMark"
        />
      </div>
    </div>
    <div class="list__foot">
      <span
        class="list__total"
        :title="totalTitle"
        data-test="exam-workspace-exam-points"
      >Totalt <strong class="list__sum">{{ totalParts.sum }}</strong><span
        v-if="totalParts.printedNote"
        class="list__printed"
      > · {{ totalParts.printedNote }}</span></span>
      <div
        class="list__actions"
        data-test="exam-workspace-footer-actions"
      >
        <button
          type="button"
          class="xw-btn xw-btn--compact xw-btn--ghost list__action"
          :class="{ 'list__action--idle': printedTotal === null }"
          :disabled="disabled"
          data-test="exam-workspace-accept-exam-total"
          @click="emit('acceptExamTotal')"
        >
          Använd {{ examWorkspaceFormatPoints(total) }} p
        </button>
        <button
          type="button"
          class="xw-btn xw-btn--compact xw-btn--ghost list__action"
          :class="{ 'list__action--idle': !anyPrintedDifference }"
          :disabled="disabled"
          data-test="exam-workspace-accept-all-totals"
          @click="emit('acceptAllTotals')"
        >
          Använd beräknade summor
        </button>
      </div>
    </div>
    <ExamWorkspaceNewItemMenu
      :open="newMenuOpen"
      :anchor="newTrigger"
      :child="false"
      @choose="emit('add', $event)"
      @close="newMenuOpen = false"
    />
  </section>
</template>

<style scoped>
.list { display: flex; flex-direction: column; min-height: 0; border-right: 1px solid var(--huleedu-surface-divider); }
.list__head {
  display: flex; align-items: center; justify-content: space-between; gap: var(--huleedu-space-3); flex: none;
  height: 52px; padding: 0 var(--huleedu-space-4) 0 var(--huleedu-space-6); border-bottom: 1px solid var(--huleedu-surface-divider);
}
.list__title { margin: 0; font-size: var(--huleedu-text-base); font-weight: var(--huleedu-font-semibold); }
.list__head-actions { display: flex; align-items: center; gap: var(--huleedu-space-2); }
.list__markbar {
  display: flex; align-items: center; gap: var(--huleedu-space-2); flex: none;
  height: calc(var(--xw-ctl-compact, 28px) + 2 * var(--huleedu-space-2));
  padding: 0 var(--huleedu-space-4) 0 var(--huleedu-space-6);
  border-bottom: 1px solid var(--huleedu-surface-divider);
}
/* The group action keeps its box in both states; hidden when the list is not marking. */
.list__markbar-group--idle { visibility: hidden; }
/* One slot for Markera/Avbryt: a fixed width so swapping the label moves nothing. */
.list__markbar-toggle { min-width: 100px; }
.list__scroll { flex: 1; min-height: 0; overflow-y: auto; }
.list__intro {
  padding: var(--huleedu-space-1-5) var(--huleedu-space-4) var(--huleedu-space-1-5) var(--huleedu-space-6);
  border-bottom: 1px solid var(--huleedu-surface-divider);
}
.list__intro--selected { background: var(--huleedu-action-10); box-shadow: inset 4px 0 0 var(--huleedu-action); }
.list__instructions {
  all: unset; box-sizing: border-box; display: flex; flex-direction: column; width: 100%; min-width: 0;
  padding: var(--huleedu-space-1) 0; cursor: pointer;
}
.list__instructions:focus-visible { outline: 2px solid var(--huleedu-action-40); outline-offset: 2px; }
.list__instructions-title { font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-medium); }
.list__instructions-preview {
  display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden;
  font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60);
}
.list__foot {
  display: flex; flex-direction: column; gap: var(--huleedu-space-1); flex: none;
  padding: var(--huleedu-space-2) var(--huleedu-space-6); border-top: 1px solid var(--huleedu-surface-divider);
  font-size: var(--huleedu-text-sm);
}
/* Two lines of fixed height: the sum with its note, then the action slot; accepting a total changes neither. */
.list__total {
  flex: none; height: 20px; line-height: 20px; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.list__sum { font-weight: var(--huleedu-font-semibold); }
.list__printed { color: var(--huleedu-warning); }
/* The ghost buttons' own padding spaces them, so the slot reaches past the footer padding to hold both on one line. */
.list__actions {
  display: flex; flex-wrap: nowrap; align-items: center; flex: none;
  height: var(--xw-ctl-compact, 28px); margin-inline: calc(-1 * var(--huleedu-workbench-control-padding-inline));
}
.list__action--idle { visibility: hidden; }
@media (max-width: 1279px) {
  .list__head { padding: 0 var(--huleedu-space-3) 0 var(--huleedu-space-4); }
  .list__markbar { padding: 0 var(--huleedu-space-3) 0 var(--huleedu-space-4); }
  .list__foot { padding: var(--huleedu-space-2) var(--huleedu-space-4); }
  .list__intro { padding-left: var(--huleedu-space-4); padding-right: var(--huleedu-space-3); }
}
@media (max-width: 767px) {
  .list { display: none; }
  .list--overlay {
    display: flex; position: fixed; inset: 0; z-index: 25; border: 0; background: var(--huleedu-canvas);
  }
  .list__head { height: 56px; padding: 0 var(--huleedu-space-4); }
  .list__title { flex: 1; }
}
</style>
