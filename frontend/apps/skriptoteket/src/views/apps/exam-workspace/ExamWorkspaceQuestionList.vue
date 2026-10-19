<script setup lang="ts">
/**
 * Exam workspace question list column.
 *
 * Domain purpose:
 *   Every question of the open exam in order under "Frågor (N)", with "Ny
 *   uppgift" adding a question or an instruction with deluppgifter after the
 *   selected one. The footer holds the exam total ("Totalt N p", cut with an
 *   ellipsis, the full text in a tooltip) at a fixed height. One neutral
 *   line per printed total that differs from its questions' sum floats over
 *   the bottom edge of the scrolling list directly above the footer: the
 *   exam line first, then one line per differing part in document order.
 *   The lines are absolutely positioned, so adding or removing a line never
 *   changes the size of the scrolling list or the footer. The scroll content
 *   always ends with a fixed one-row end room of one line's height, on every
 *   exam, so the scroll height never changes when a line appears, goes or
 *   returns on undo. Each line is
 *   followed by two compact glyph-only buttons: confirm ("Godta frågornas
 *   summa, {sum} p", clears that line's own stored printed total) and
 *   continue ("Visa frågorna", selects the line's target, hidden when the
 *   line has none).
 *   A line goes as soon as its level agrees. Above the rows the exam
 *   instruction is one entry: "Instruktioner" with a short preview when the
 *   exam has one, otherwise a quiet "Lägg till instruktioner"; both open it in
 *   the editor. On desktop the list collapses to a rail and resizes with a
 *   handle. On a phone the list
 *   opens full screen over the editor from the question strip and closes
 *   with Tillbaka or a choice. "Markera" turns the list into Markera mode: a
 *   standalone question carries a checkbox (an ordering question's is
 *   disabled, G6) and a bar at the top groups the ticked questions into a new
 *   part (G2, G11); a part and a question inside a part carry no checkbox.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; the lines come from
 *     `examWorkspaceNoteLines` (the `mismatches` from `examWorkspaceTotals`
 *     with the list's entry labels) and render through
 *     `ExamWorkspaceNoteLine`; the list never recomputes the difference.
 */

import { computed, nextTick, ref, watch } from "vue";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceColumnHandle from "./ExamWorkspaceColumnHandle.vue";
import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";
import ExamWorkspaceNoteLine from "./ExamWorkspaceNoteLine.vue";
import type { ExamWorkspaceNoteLineAction } from "./ExamWorkspaceNoteLine.vue";
import ExamWorkspaceQuestionRow from "./ExamWorkspaceQuestionRow.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { buildExamWorkspaceNoteLines } from "./examWorkspaceNoteLines";
import type { ExamWorkspaceNoteLine as NoteLine } from "./examWorkspaceNoteLines";
import { examWorkspaceFormatExactPoints, examWorkspaceFormatPoints } from "./examWorkspaceTotals";
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";
import { EXAM_INSTRUCTIONS_ENTRY_ID } from "./useExamWorkspaceSelection";

const props = withDefaults(
  defineProps<{
    entries: ExamWorkspaceListEntry[];
    selectedId: string | null;
    /** The start of the exam instruction's text, or `null` when the exam has none. */
    examInstructionsPreview: string | null;
    questionCount: number;
    total: number;
    /** One entry per printed total that differs from its questions' sum: the exam first, then parts in order. */
    mismatches: PrintedTotalMismatch[];
    canAdd: boolean;
    /** The workspace is busy: the lines' buttons wait like the list's other actions. */
    disabled: boolean;
    /** The phone shows the list as a full-screen layer. */
    overlay: boolean;
    /** The desktop list is collapsed to its rail; only ever set on desktop. */
    collapsed?: boolean;
    /** The desktop resize handle is wanted; only ever set on desktop. */
    handle?: boolean;
  }>(),
  { collapsed: false, handle: false },
);

const examInstructionsSelected = computed(() => props.selectedId === EXAM_INSTRUCTIONS_ENTRY_ID);
/** The exam total line in full, for the tooltip when a long total is cut by the ellipsis. */
const totalTitle = computed(() => `Totalt ${formattedTotal.value}`);

const emit = defineEmits<{
  select: [id: string];
  add: [kind: TeacherItemKind | "instruction" | "part"];
  group: [itemIds: string[]];
  clearPrintedTotal: [parentId: string | null];
  close: [];
  /** The resize handle reports a dragged or stepped width in px. */
  set: [px: number];
  /** The resize handle resets to the default width on double-click. */
  reset: [];
  /** The collapse glyph, the expand glyph or Enter on the handle. */
  "toggle-collapse": [];
}>();

/** The footer note lines in order, named with the list's part numbers. */
const lines = computed<NoteLine[]>(() => buildExamWorkspaceNoteLines(props.mismatches, props.entries));

/** Each line's glyph-only actions; a second line kind adds its branch here. */
function actionsFor(line: NoteLine): ExamWorkspaceNoteLineAction[] {
  switch (line.kind) {
    case "printed-total": {
      const changeLabel = `Godta frågornas summa, ${examWorkspaceFormatExactPoints(line.sum)} p`;
      const actions: ExamWorkspaceNoteLineAction[] = [
        { dataTest: "exam-workspace-printed-total-change", key: "change", label: changeLabel, meaning: "confirm" },
      ];
      if (line.target !== null) {
        actions.push({ dataTest: "exam-workspace-printed-total-show", key: "show", label: "Visa frågorna", meaning: "continue" });
      }
      return actions;
    }
    default: {
      const exhaustive: never = line.kind;
      return exhaustive;
    }
  }
}

function handleNoteAction(line: NoteLine, key: string): void {
  switch (line.kind) {
    case "printed-total":
      if (key === "change") {
        emit("clearPrintedTotal", line.parentId);
        return;
      }
      if (key === "show" && line.target !== null) {
        emit("select", line.target);
        return;
      }
      return;
    default: {
      const exhaustive: never = line.kind;
      return exhaustive;
    }
  }
}

const formattedTotal = computed(() => `${examWorkspaceFormatPoints(props.total)} p`);

const rows = ref<HTMLElement | null>(null);
const newTrigger = ref<HTMLButtonElement | null>(null);
const newMenuOpen = ref(false);
const collapseGlyph = ref<HTMLButtonElement | null>(null);
const expandGlyph = ref<HTMLButtonElement | null>(null);

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

/**
 * The collapse and expand glyphs replace each other across branches, so a
 * glyph click moves focus to its replacement on the next tick. Handle-driven
 * toggles keep focus on the one handle, which stays mounted in both states.
 */
async function collapseFromGlyph(): Promise<void> {
  emit("toggle-collapse");
  await nextTick();
  expandGlyph.value?.focus();
}

async function expandFromGlyph(): Promise<void> {
  emit("toggle-collapse");
  await nextTick();
  collapseGlyph.value?.focus();
}
</script>

<template>
  <section
    class="list"
    :class="{ 'list--overlay': overlay, 'list--collapsed': collapsed }"
    aria-labelledby="exam-workspace-list-title"
    data-test="exam-workspace-question-list"
  >
    <template v-if="collapsed">
      <div class="list__rail">
        <button
          ref="expandGlyph"
          type="button"
          class="xw-btn xw-btn--icon xw-btn--ghost"
          aria-label="Visa frågelistan"
          title="Visa frågelistan"
          data-test="exam-workspace-list-expand"
          @click="expandFromGlyph"
        >
          <UiGlyph
            meaning="expand"
            :size="20"
          />
        </button>
      </div>
    </template>
    <template v-else>
      <div class="list__frame">
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
              v-if="handle"
              ref="collapseGlyph"
              type="button"
              class="xw-btn xw-btn--icon xw-btn--ghost"
              aria-label="Dölj frågelistan"
              title="Dölj frågelistan"
              data-test="exam-workspace-list-collapse"
              @click="collapseFromGlyph"
            >
              <UiGlyph
                meaning="toggle-sidebar"
                :size="20"
              />
            </button>
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
          <div
            class="list__end-room"
            aria-hidden="true"
            data-test="exam-workspace-list-end-room"
          />
        </div>
        <div
          v-if="lines.length > 0"
          class="list__printed-lines"
          data-test="exam-workspace-printed-total-lines"
        >
          <ExamWorkspaceNoteLine
            v-for="line in lines"
            :key="line.key"
            data-test="exam-workspace-printed-total-line"
            :text="line.text"
            :actions="actionsFor(line)"
            :disabled="disabled"
            @action="handleNoteAction(line, $event)"
          />
        </div>
        <div class="list__foot">
          <span
            class="list__total"
            :title="totalTitle"
            data-test="exam-workspace-exam-points"
          >Totalt <strong class="list__sum">{{ formattedTotal }}</strong></span>
        </div>
        <ExamWorkspaceNewItemMenu
          :open="newMenuOpen"
          :anchor="newTrigger"
          :child="false"
          @choose="emit('add', $event)"
          @close="newMenuOpen = false"
        />
      </div>
    </template>
    <ExamWorkspaceColumnHandle
      v-if="handle"
      edge="list"
      column="list"
      controls="exam-workspace-question-list"
      label="Ändra bredd på frågelistan"
      collapsible
      :collapsed="collapsed"
      @set="emit('set', $event)"
      @reset="emit('reset')"
      @toggle-collapse="emit('toggle-collapse')"
    />
  </section>
</template>

<style scoped>
.list { display: flex; flex-direction: column; min-height: 0; position: relative; border-right: 1px solid var(--huleedu-surface-divider); }
.list__frame { display: flex; flex-direction: column; flex: 1; min-height: 0; min-width: 0; position: relative; }
/* The collapsed desktop list is a 44px rail with one expand glyph and the draggable edge. */
.list__rail { display: flex; justify-content: center; padding: var(--huleedu-space-2) 0; }
@media (min-width: 1280px) {
  /* Below its minimum the list keeps its minimum layout and scrolls inside itself. */
  .list__frame { overflow-x: auto; }
  .list:not(.list--collapsed) .list__frame > .list__head,
  .list:not(.list--collapsed) .list__frame > .list__markbar,
  .list:not(.list--collapsed) .list__frame > .list__scroll,
  .list:not(.list--collapsed) .list__frame > .list__printed-lines,
  .list:not(.list--collapsed) .list__frame > .list__foot { min-width: var(--xw-list-min); }
}
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
/* The fixed one-row end room: one note line's height at the end of the scroll
   content on every exam, so the scroll height never changes when a floating
   line appears, goes or returns on undo. */
.list__end-room { flex: none; height: var(--xw-note-line); }
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
  display: -webkit-box; -webkit-orient: vertical; -webkit-line-clamp: 2; overflow: hidden;
  font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60);
}
.list__foot {
  display: flex; flex-direction: column; justify-content: center; flex: none;
  height: var(--xw-list-foot);
  padding: 0 var(--huleedu-space-6); border-top: 1px solid var(--huleedu-surface-divider);
  font-size: var(--huleedu-text-sm); color: var(--huleedu-navy);
}
/* The total line keeps its height whether the mismatch lines show or not. */
.list__total {
  flex: none; height: 20px; line-height: 20px; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.list__sum { font-weight: var(--huleedu-font-semibold); }
/* The floating mismatch lines: absolutely positioned over the bottom edge of
   the scrolling list directly above the footer, so adding or removing a line
   never changes the size of the scroll viewport or the footer. With two or
   more lines the extra lines stack upward over the list and may cover the
   last rows at the very end. The opaque list surface keeps the rows under
   them from showing through. */
.list__printed-lines {
  position: absolute; left: 0; right: 0; bottom: var(--xw-list-foot); z-index: 2;
  display: flex; flex-direction: column; gap: var(--huleedu-space-1);
  padding: 0 var(--huleedu-space-6); background: var(--huleedu-canvas);
}
@media (max-width: 1279px) {
  .list__head { padding: 0 var(--huleedu-space-3) 0 var(--huleedu-space-4); }
  .list__markbar { padding: 0 var(--huleedu-space-3) 0 var(--huleedu-space-4); }
  .list__foot { padding: 0 var(--huleedu-space-4); }
  .list__printed-lines { padding: 0 var(--huleedu-space-4); }
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
