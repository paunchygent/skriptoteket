<script setup lang="ts">
/**
 * Exam workspace new-question menu.
 *
 * Domain purpose:
 *   The kinds a teacher adds from "Ny uppgift" (a standalone question, an
 *   instruction with deluppgifter, or an empty part) and from "+ Deluppgift".
 *   Ordering questions are standalone only (ST-SKRIPT-39-06 P3), so the
 *   deluppgift menu omits Ordna; only the top-level menu offers Ny del (G9).
 *
 * Relationships:
 *   - Opened by `ExamWorkspaceQuestionList` and `ExamWorkspaceInstructionEditor`.
 */

import { computed } from "vue";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import { EXAM_WORKSPACE_NEW_ITEM_KINDS } from "./examWorkspaceStructure";

const emit = defineEmits<{
  choose: [kind: TeacherItemKind | "instruction" | "part"];
  close: [];
}>();

const props = defineProps<{
  open: boolean;
  anchor: HTMLElement | null;
  child: boolean;
}>();

/** Ordering questions are standalone only (ST-SKRIPT-39-06 P3), so a deluppgift never offers them. */
const entries = computed(() =>
  EXAM_WORKSPACE_NEW_ITEM_KINDS.filter((entry) => !(props.child && entry.kind === "ordering")),
);

function choose(kind: TeacherItemKind | "instruction" | "part"): void {
  emit("close");
  emit("choose", kind);
}
</script>

<template>
  <ExamWorkspaceMenu
    :open="open"
    :anchor="anchor"
    :label="child ? 'Ny deluppgift' : 'Ny uppgift'"
    :test-id="child ? 'exam-workspace-new-child-menu' : 'exam-workspace-new-menu'"
    @close="emit('close')"
  >
    <div class="xw-mhead">
      {{ child ? "Ny deluppgift" : "Ny fråga" }}
    </div>
    <button
      v-for="entry in entries"
      :key="entry.kind"
      type="button"
      class="xw-mi"
      role="menuitem"
      :data-test="`exam-workspace-new-${entry.kind}`"
      @click="choose(entry.kind)"
    >
      <span class="xw-mi__pad" /><span class="xw-grow">{{ entry.label }}</span>
    </button>
    <template v-if="!child">
      <div class="xw-mdiv" />
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        data-test="exam-workspace-new-instruction"
        @click="choose('instruction')"
      >
        <UiGlyph
          meaning="instruction"
          :size="20"
        /><span class="xw-grow">Instruktion med deluppgifter</span>
      </button>
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        data-test="exam-workspace-new-part"
        @click="choose('part')"
      >
        <UiGlyph
          meaning="add"
          :size="20"
        /><span class="xw-grow">Ny del</span>
      </button>
    </template>
  </ExamWorkspaceMenu>
</template>
