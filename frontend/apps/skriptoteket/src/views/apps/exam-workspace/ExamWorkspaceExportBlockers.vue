<script setup lang="ts">
/**
 * Exam workspace "Kan inte exporteras ännu" panel.
 *
 * Domain purpose:
 *   Every question that stops the export, one row each in the list's words
 *   ("Fråga 3: facit saknas"). The row leads to the question and the field
 *   to fix; its button makes the fix in place where the workspace can, so
 *   the formats enable as soon as the last row is gone (user rule 2026-10-17).
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceExportMenu` and `ExamWorkspaceExportDrawer`;
 *     the rows come from `examWorkspaceBlockers`.
 */

import { UiGlyph } from "../../../components/ui";
import { EXAM_WORKSPACE_BLOCKER_FIX_LABELS } from "./examWorkspaceBlockers";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";

defineProps<{
  blockers: ExamWorkspaceBlockerEntry[];
  /** No fix runs while the exam is busy; an AI key suggestion runs one at a time. */
  fixDisabled: boolean;
  suggestBusy: boolean;
  testId: string;
}>();

const emit = defineEmits<{
  goto: [blocker: ExamWorkspaceBlockerEntry];
  fix: [blocker: ExamWorkspaceBlockerEntry];
}>();
</script>

<template>
  <div
    class="xw-mblock"
    :data-test="testId"
  >
    <b><UiGlyph
      meaning="status-failure"
      :size="16"
    />Kan inte exporteras ännu</b>
    <div
      v-for="blocker in blockers"
      :key="blocker.itemId"
      class="xw-mblock__row"
    >
      <button
        type="button"
        class="xw-mblock__go"
        :data-test="`exam-workspace-blocker-${blocker.itemId}`"
        @click="emit('goto', blocker)"
      >
        Fråga {{ blocker.label }}: {{ blocker.problem }}
      </button>
      <button
        v-if="blocker.fix"
        type="button"
        class="xw-mblock__fix"
        :disabled="fixDisabled || (blocker.fix === 'suggest_key' && suggestBusy)"
        :aria-label="`Fråga ${blocker.label}: ${EXAM_WORKSPACE_BLOCKER_FIX_LABELS[blocker.fix]}`"
        :data-test="`exam-workspace-blocker-fix-${blocker.itemId}`"
        @click="emit('fix', blocker)"
      >
        {{ EXAM_WORKSPACE_BLOCKER_FIX_LABELS[blocker.fix] }}
      </button>
    </div>
  </div>
</template>
