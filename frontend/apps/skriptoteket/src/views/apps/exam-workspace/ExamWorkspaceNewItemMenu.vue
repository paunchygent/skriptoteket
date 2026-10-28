<script setup lang="ts">
/**
 * Exam workspace new-question menu.
 *
 * Domain purpose:
 *   The kinds a teacher adds from "Ny uppgift" (a standalone question, an
 *   instruction with deluppgifter, or an empty part) and from "+ Deluppgift".
 *   Both menus offer every question kind, Ordna included: an ordering question
 *   may sit inside a part, where it is always worth 1 point
 *   (TASK-SKRIPT-39-06-11 D1). Only the top-level menu offers Ny del (G9).
 *
 * Relationships:
 *   - Opened by `ExamWorkspaceQuestionList` and `ExamWorkspaceInstructionEditor`.
 */

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import { EXAM_WORKSPACE_NEW_ITEM_KINDS } from "./examWorkspaceStructure";

const emit = defineEmits<{
  choose: [kind: TeacherItemKind | "instruction" | "part"];
  close: [];
}>();

defineProps<{
  open: boolean;
  anchor: HTMLElement | null;
  child: boolean;
}>();

/** Every question kind, Ordna included, is offered in a part's menu too (TASK-SKRIPT-39-06-11 D1). */
const entries = EXAM_WORKSPACE_NEW_ITEM_KINDS;

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
