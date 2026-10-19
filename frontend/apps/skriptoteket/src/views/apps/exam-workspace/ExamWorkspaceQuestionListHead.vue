<script setup lang="ts">
/**
 * Exam workspace question list head row.
 *
 * Domain purpose:
 *   The one 40 px row above the list: the title "Frågor (N)", a spacer, then
 *   one tool group with the collapse glyph (only when the desktop handle is
 *   wanted), Ny uppgift and the Markera toggle. On a phone the full-screen
 *   list also carries a Tillbaka button before the title. Ny uppgift opens
 *   the new-question menu, which this row owns with its trigger; the row
 *   reports the chosen kind. The row grows to 44 px tools on a coarse pointer
 *   and to 56 px on a phone.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionList`, which owns the Markera state,
 *     the collapse and the add command; the title's id labels the list.
 */

import { ref } from "vue";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";

defineProps<{
  questionCount: number;
  /** The phone shows the list as a full-screen layer with a Tillbaka button. */
  overlay: boolean;
  /** The desktop resize handle is wanted, so the collapse glyph shows. */
  handle: boolean;
  canAdd: boolean;
  /** The Markera mode is on. */
  marking: boolean;
  /** The workspace is busy: Markera waits like the list's other actions. */
  disabled: boolean;
}>();

const emit = defineEmits<{
  close: [];
  add: [kind: TeacherItemKind | "instruction" | "part"];
  "toggle-collapse": [];
  "toggle-marking": [];
}>();

const newTrigger = ref<HTMLButtonElement | null>(null);
const newMenuOpen = ref(false);
const collapseGlyph = ref<HTMLButtonElement | null>(null);

/** The list moves focus here after its expand glyph, which this glyph replaces, was pressed. */
function focusCollapse(): void {
  collapseGlyph.value?.focus();
}

defineExpose({ focusCollapse });
</script>

<template>
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
    <span
      class="list__spacer"
      aria-hidden="true"
    />
    <div class="xw-tools">
      <button
        v-if="handle"
        ref="collapseGlyph"
        type="button"
        class="xw-tool"
        aria-label="Dölj frågelistan"
        title="Dölj frågelistan"
        data-test="exam-workspace-list-collapse"
        @click="emit('toggle-collapse')"
      >
        <UiGlyph
          meaning="toggle-sidebar"
          :size="16"
        />
      </button>
      <button
        ref="newTrigger"
        type="button"
        class="xw-tool"
        :disabled="!canAdd"
        aria-haspopup="menu"
        :aria-expanded="newMenuOpen"
        aria-label="Ny uppgift"
        title="Ny uppgift"
        data-test="exam-workspace-new"
        @click="newMenuOpen = !newMenuOpen"
      >
        <UiGlyph
          meaning="add"
          :size="16"
        />
      </button>
      <button
        type="button"
        class="xw-tool"
        :aria-pressed="marking"
        :disabled="disabled"
        aria-label="Markera frågor"
        title="Markera frågor"
        data-test="exam-workspace-marking-toggle"
        @click="emit('toggle-marking')"
      >
        <UiGlyph
          :meaning="marking ? 'checkbox-on' : 'checkbox-off'"
          :size="16"
        />
      </button>
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

<style scoped>
/* One 40 px row: title, a spacer, then the in-content tools 2 px apart. */
.list__head {
  display: flex; align-items: center; gap: var(--huleedu-space-2); flex: none;
  height: calc(var(--huleedu-workbench-control-height) + 2 * var(--huleedu-space-1-5));
  padding: 0 var(--huleedu-space-2) 0 var(--huleedu-space-4); border-bottom: 1px solid var(--huleedu-surface-divider);
}
/* The title is never truncated. */
.list__title {
  flex: none; margin: 0; white-space: nowrap;
  font-size: var(--huleedu-type-control-value-size); font-weight: var(--huleedu-font-semibold);
}
.list__spacer { flex: 1; min-width: 0; }
/* On a coarse pointer the tools grow to 44 px, so the row keeps the same inset around them. */
@media (pointer: coarse) {
  .list__head { height: calc(var(--huleedu-action-control-height) + 2 * var(--huleedu-space-1-5)); }
}
@media (max-width: 767px) {
  .list__head { height: 56px; padding: 0 var(--huleedu-space-4); }
}
</style>
