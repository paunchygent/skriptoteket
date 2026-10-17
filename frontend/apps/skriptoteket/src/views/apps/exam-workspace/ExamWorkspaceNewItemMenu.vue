<script setup lang="ts">
/**
 * Exam workspace new-question menu.
 *
 * Domain purpose:
 *   The kinds a teacher adds from "Ny uppgift" (a standalone question, or an
 *   instruction with deluppgifter) and from "+ Deluppgift". Ordning keeps a
 *   reserved, disabled place marked "Kommer senare" until TASK-SKRIPT-39-06-02
 *   decides whether ordering is built (user 2026-10-17); ordering questions
 *   are standalone only (ST-SKRIPT-39-06 P3), so the deluppgift menu omits it.
 *
 * Relationships:
 *   - Opened by `ExamWorkspaceQuestionList` and `ExamWorkspaceInstructionEditor`.
 */

import { useId } from "vue";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import { EXAM_WORKSPACE_NEW_ITEM_KINDS } from "./examWorkspaceStructure";

defineProps<{
  open: boolean;
  anchor: HTMLElement | null;
  child: boolean;
}>();

const emit = defineEmits<{
  choose: [kind: TeacherItemKind | "instruction"];
  close: [];
}>();

const hintId = useId();

function choose(kind: TeacherItemKind | "instruction"): void {
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
      v-for="entry in EXAM_WORKSPACE_NEW_ITEM_KINDS"
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
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        aria-disabled="true"
        tabindex="-1"
        :aria-describedby="hintId"
        data-test="exam-workspace-new-ordning"
      >
        <span class="xw-mi__pad" /><span class="xw-grow">Ordning</span><span
          :id="hintId"
          class="xw-mi__hint"
        >Kommer senare</span>
      </button>
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
    </template>
  </ExamWorkspaceMenu>
</template>
