<script setup lang="ts">
/**
 * Exam workspace question list column.
 *
 * Domain purpose:
 *   Every question of the open exam in order under "Frågor (N)", with "Ny
 *   uppgift" adding a question or an instruction with deluppgifter after the
 *   selected one, and a footer with the exam total, which says in amber
 *   when the exam text prints another total. The exam's shared instructions, when it has any,
 *   come in through the `intro` slot above the rows. On a phone the list
 *   opens full screen over the editor from the question strip and closes
 *   with Tillbaka or a choice.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; rows are `ExamWorkspaceQuestionRow`,
 *     each told only whether it is selected.
 */

import { nextTick, ref, watch } from "vue";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";
import ExamWorkspaceQuestionRow from "./ExamWorkspaceQuestionRow.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspacePointsLine } from "./examWorkspaceTotals";

const props = defineProps<{
  entries: ExamWorkspaceListEntry[];
  selectedId: string | null;
  questionCount: number;
  total: number;
  /** The exam total the exam text prints, only when it differs from `total`. */
  printedTotal: number | null;
  canAdd: boolean;
  /** The phone shows the list as a full-screen layer. */
  overlay: boolean;
}>();

const emit = defineEmits<{
  select: [id: string];
  add: [kind: TeacherItemKind | "instruction"];
  close: [];
}>();

const rows = ref<HTMLElement | null>(null);
const newTrigger = ref<HTMLButtonElement | null>(null);
const newMenuOpen = ref(false);

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
    <div class="list__scroll">
      <slot name="intro" />
      <div
        ref="rows"
        class="list__rows"
        role="listbox"
        aria-labelledby="exam-workspace-list-title"
        aria-keyshortcuts="ArrowUp ArrowDown"
      >
        <ExamWorkspaceQuestionRow
          v-for="entry in entries"
          :key="entry.id"
          :entry="entry"
          :selected="entry.id === selectedId"
          @select="emit('select', $event)"
        />
      </div>
    </div>
    <div class="list__foot">
      <span
        id="exam-workspace-exam-points"
        class="list__total"
        :class="{ 'list__total--printed': printedTotal !== null }"
        tabindex="-1"
        data-test="exam-workspace-exam-points"
      >Totalt {{ examWorkspacePointsLine(total, printedTotal) }}</span>
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
.list__scroll { flex: 1; min-height: 0; overflow-y: auto; }
.list__foot {
  display: flex; align-items: center; gap: var(--huleedu-space-2); flex: none; min-height: 44px;
  padding: var(--huleedu-space-2) var(--huleedu-space-6); border-top: 1px solid var(--huleedu-surface-divider);
  font-size: var(--huleedu-text-sm);
}
.list__total { min-width: 0; overflow-wrap: anywhere; outline: none; }
.list__total:focus-visible { outline: 2px solid var(--huleedu-action-40); outline-offset: 2px; }
.list__total--printed { color: var(--huleedu-warning); }
@media (max-width: 1279px) {
  .list__head { padding: 0 var(--huleedu-space-3) 0 var(--huleedu-space-4); }
  .list__foot { padding: var(--huleedu-space-2) var(--huleedu-space-4); }
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
