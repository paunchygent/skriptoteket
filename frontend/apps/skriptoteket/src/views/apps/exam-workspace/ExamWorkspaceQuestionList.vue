<script setup lang="ts">
/**
 * Exam workspace question list column.
 *
 * Domain purpose:
 *   Every question of the open exam in order under "Frågor (N)", with "Ny
 *   uppgift" adding a question or an instruction with deluppgifter after the
 *   selected one. The footer holds the exam total ("Totalt N p", cut with an
 *   ellipsis, the full text in a tooltip) with the amber points note below
 *   it while the exam text prints another total: one jump row per
 *   difference, then "Använd beräknade poäng?" with the no and yes
 *   glyph-only answers. Dismissed, the footer greys the printed part
 *   ("Totalt N p · provtexten anger M p") and the note stays hidden.
 *   Above the rows the exam
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
 *     each told only whether it is selected. The points note renders the
 *     `PrintedTotalAccount` from `examWorkspaceTotals` with the list's
 *     entry labels; it never recomputes the difference.
 */

import { computed, nextTick, ref, watch } from "vue";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";
import ExamWorkspaceQuestionRow from "./ExamWorkspaceQuestionRow.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspaceFormatPoints } from "./examWorkspaceTotals";
import type { PrintedTotalAccount } from "./examWorkspaceTotals";
import { EXAM_INSTRUCTIONS_ENTRY_ID } from "./useExamWorkspaceSelection";

const props = defineProps<{
  entries: ExamWorkspaceListEntry[];
  selectedId: string | null;
  /** The start of the exam instruction's text, or `null` when the exam has none. */
  examInstructionsPreview: string | null;
  questionCount: number;
  total: number;
  /** The printed-total account behind the points note, or `null` while nothing differs. */
  account: PrintedTotalAccount | null;
  /** The exam total itself differs from the questions' sum (the note's exam heading and the grey footer line). */
  examDiffers: boolean;
  canAdd: boolean;
  /** The workspace is busy: the note's answers and jump rows wait like the other list actions. */
  disabled: boolean;
  /** The phone shows the list as a full-screen layer. */
  overlay: boolean;
}>();

const examInstructionsSelected = computed(() => props.selectedId === EXAM_INSTRUCTIONS_ENTRY_ID);
/** The exam total line in full, for the tooltip when a long dismissed note is cut by the ellipsis. */
const totalTitle = computed(() =>
  dismissedNote.value === null ? undefined : `Totalt ${formattedTotal.value} · ${dismissedNote.value}`,
);

const emit = defineEmits<{
  select: [id: string];
  add: [kind: TeacherItemKind | "instruction" | "part"];
  group: [itemIds: string[]];
  dismissPrintedTotal: [];
  useComputedPoints: [];
  close: [];
}>();

/** One rendered line of the points note: the text with its jump target, or `null` for the remainder. */
type PointsNoteRow = { key: string; text: string; target: string | null };

const entryById = computed(() => new Map(props.entries.map((entry) => [entry.id, entry])));

/** The note shows while the account names a difference that is not dismissed. */
const showNote = computed(() => props.account !== null && !props.account.dismissed);

/** Dismissed with an exam-level difference: the footer keeps the printed total in neutral grey. */
const showDismissedPrinted = computed(
  () => props.account !== null && props.account.dismissed && props.examDiffers && props.account.printed !== null,
);

const formattedTotal = computed(() => `${examWorkspaceFormatPoints(props.total)} p`);

const dismissedNote = computed(() => {
  const printed = props.account?.printed;
  return showDismissedPrinted.value && printed !== null && printed !== undefined
    ? `provtexten anger ${examWorkspaceFormatPoints(printed)} p`
    : null;
});

const noteHeading = computed(() => {
  const printed = props.account?.printed;
  return props.examDiffers && printed !== null && printed !== undefined
    ? `Provtexten anger ${examWorkspaceFormatPoints(printed)} p. Dessa skiljer sig:`
    : "Dessa skiljer sig från provtexten:";
});

/** The account's rows named with the list's labels, in document order. */
const noteRows = computed<PointsNoteRow[]>(() => {
  const account = props.account;
  if (account === null) {
    return [];
  }
  return account.rows.flatMap((row, index): PointsNoteRow[] => {
    if (row.kind === "part") {
      const entry = entryById.value.get(row.parentId);
      if (!entry || entry.kind !== "parent") {
        return [];
      }
      return [{
        key: `part-${row.parentId}`,
        target: row.parentId,
        text: `${entry.text} — provtexten ${examWorkspaceFormatPoints(row.printed)} p, nu ${examWorkspaceFormatPoints(row.now)} p`,
      }];
    }
    if (row.kind === "question") {
      const entry = entryById.value.get(row.itemId);
      if (!entry || entry.kind !== "item") {
        return [];
      }
      const label = `Fråga ${entry.label}`;
      if (row.now === null) {
        return [{
          key: `question-${row.itemId}`,
          target: row.itemId,
          text:
            row.source === null
              ? `${label} — saknar poäng`
              : `${label} — provtexten ${examWorkspaceFormatPoints(row.source)} p, saknar poäng`,
        }];
      }
      if (row.source === null) {
        return [{
          key: `question-${row.itemId}`,
          target: row.itemId,
          text: `${label} — nu ${examWorkspaceFormatPoints(row.now)} p`,
        }];
      }
      return [{
        key: `question-${row.itemId}`,
        target: row.itemId,
        text: `${label} — provtexten ${examWorkspaceFormatPoints(row.source)} p, nu ${examWorkspaceFormatPoints(row.now)} p`,
      }];
    }
    return [{
      key: `remainder-${index}`,
      target: null,
      text:
        row.points > 0
          ? `Övriga ${examWorkspaceFormatPoints(row.points)} p finns inte i någon fråga`
          : `${examWorkspaceFormatPoints(Math.abs(row.points))} p fler än provtexten anger`,
    }];
  });
});

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
          @toggle-mark="toggleMark"
        />
      </div>
    </div>
    <div class="list__foot">
      <span
        class="list__total"
        :title="totalTitle"
        data-test="exam-workspace-exam-points"
      >Totalt <strong class="list__sum">{{ formattedTotal }}</strong><span
        v-if="dismissedNote"
        class="list__dismissed"
      > · {{ dismissedNote }}</span></span>
      <aside
        v-if="showNote"
        class="list__note"
        data-test="exam-workspace-points-note"
      >
        <p class="list__note-head">{{ noteHeading }}</p>
        <ul class="list__note-rows">
          <li
            v-for="row in noteRows"
            :key="row.key"
            class="list__note-item"
          >
            <button
              v-if="row.target !== null"
              type="button"
              class="list__note-row"
              :disabled="disabled"
              data-test="exam-workspace-points-note-row"
              @click="emit('select', row.target)"
            >
              <UiGlyph
                meaning="continue"
                :size="16"
              /><span class="list__note-text">{{ row.text }}</span>
            </button>
            <span
              v-else
              class="list__note-row list__note-row--static"
              data-test="exam-workspace-points-note-row"
            >
              <UiGlyph
                meaning="continue"
                :size="16"
              /><span class="list__note-text">{{ row.text }}</span>
            </span>
          </li>
        </ul>
        <p class="list__note-decide">
          <span class="list__note-question">Använd beräknade poäng?</span>
          <button
            type="button"
            class="list__note-no"
            :disabled="disabled"
            aria-label="Nej, behåll provtextens poäng"
            title="Nej, behåll provtextens poäng"
            data-test="exam-workspace-points-keep"
            @click="emit('dismissPrintedTotal')"
          >
            <UiGlyph
              meaning="close"
              :size="20"
            />
          </button>
          <button
            type="button"
            class="list__note-yes"
            :disabled="disabled"
            aria-label="Ja, använd beräknade poäng"
            title="Ja, använd beräknade poäng"
            data-test="exam-workspace-points-use-computed"
            @click="emit('useComputedPoints')"
          >
            <UiGlyph
              meaning="confirm"
              :size="18"
            />
          </button>
        </p>
      </aside>
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
/* The total line keeps its height whether the note or the dismissed printed part shows. */
.list__total {
  flex: none; height: 20px; line-height: 20px; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.list__sum { font-weight: var(--huleedu-font-semibold); }
.list__dismissed { color: var(--huleedu-navy-60); }
/* The points note: amber information below the total, scrolling inside the footer when long. */
.list__note {
  background: var(--huleedu-warning-15); border: 1px solid var(--huleedu-warning-50);
  border-radius: var(--huleedu-radius-md); padding: var(--huleedu-space-2-5) var(--huleedu-space-3);
  color: var(--huleedu-warning-strong); max-height: 320px; max-height: 40%; overflow-y: auto; min-height: 0;
}
.list__note-head { margin: 0 0 var(--huleedu-space-1); font-weight: var(--huleedu-font-semibold); font-size: var(--huleedu-text-sm); }
.list__note-rows { margin: 0; padding: 0; list-style: none; }
.list__note-item + .list__note-item { border-top: 1px solid var(--huleedu-warning-50); }
.list__note-row {
  all: unset; box-sizing: border-box; display: flex; align-items: center; gap: var(--huleedu-space-2);
  width: 100%; padding: var(--huleedu-space-1-5) 0; font-size: var(--huleedu-text-sm); cursor: pointer;
}
.list__note-row--static { cursor: default; }
.list__note-row:disabled { cursor: default; color: var(--huleedu-navy-40); }
.list__note-text { min-width: 0; overflow-wrap: anywhere; }
.list__note-decide {
  display: flex; align-items: center; gap: var(--huleedu-space-2-5);
  margin: var(--huleedu-space-2) 0 0; padding-top: var(--huleedu-space-2); border-top: 1px solid var(--huleedu-warning-50);
}
.list__note-question { flex: 1; min-width: 0; font-size: var(--huleedu-text-sm); color: var(--huleedu-navy); }
.list__note-no, .list__note-yes {
  flex: none; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%; padding: 0; cursor: pointer;
}
/* No is the visually primary default: a large filled navy circle, placed first. */
.list__note-no { width: 44px; height: 44px; border: 0; background: var(--huleedu-navy); color: #fff; }
/* Yes is the smaller outlined circle. */
.list__note-yes { width: 36px; height: 36px; border: 1px solid var(--huleedu-navy); background: transparent; color: var(--huleedu-navy); }
.list__note-no:disabled, .list__note-yes:disabled { cursor: not-allowed; opacity: 0.5; }
.list__note-no:focus-visible, .list__note-yes:focus-visible, .list__note-row:focus-visible {
  outline: 2px solid var(--huleedu-action-40); outline-offset: 2px;
}
@media (hover: hover) {
  .list__note-no:not(:disabled):hover { opacity: 0.85; }
  .list__note-yes:not(:disabled):hover { background: var(--huleedu-action-05); }
}
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
