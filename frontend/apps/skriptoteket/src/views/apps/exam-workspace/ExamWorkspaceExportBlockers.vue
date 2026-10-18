<script setup lang="ts">
/**
 * Exam workspace "Kan inte exporteras ännu" panel.
 *
 * Domain purpose:
 *   Every question that stops the export, one row each in the list's words
 *   ("Fråga 3: facit saknas"); a title with no letter or digit is the one
 *   row without a question ("Ge provet en titel med bokstäver eller
 *   siffror"). The row leads to the question and the field
 *   to fix; its button makes the fix in place where the workspace can, so
 *   the formats enable as soon as the last row is gone (user rule 2026-10-17).
 *   With two or more questions missing a key, one "Föreslå facit för alla"
 *   asks for every key in one request; each row then waits for its Godkänn.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceExportMenu` and `ExamWorkspaceExportDrawer`;
 *     the rows come from `examWorkspaceBlockers`.
 */

import { computed, useId } from "vue";

import { UiGlyph } from "../../../components/ui";
import { AI_ADMIN_ONLY_NOTE, useAiAccess } from "../../../composables/useAiAccess";
import { EXAM_WORKSPACE_BLOCKER_FIX_LABELS } from "./examWorkspaceBlockers";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";

const props = defineProps<{
  blockers: ExamWorkspaceBlockerEntry[];
  /** No fix runs while the exam is busy; an AI key suggestion runs one at a time. */
  fixDisabled: boolean;
  suggestBusy: boolean;
  testId: string;
}>();

const emit = defineEmits<{
  goto: [blocker: ExamWorkspaceBlockerEntry];
  fix: [blocker: ExamWorkspaceBlockerEntry];
  suggestAll: [];
}>();

const { canUseAi } = useAiAccess();
const aiNoteId = useId();
const missingKeys = computed(() => props.blockers.filter((blocker) => blocker.fix === "suggest_key").length);
/**
 * At least one answer-key control is on screen: each question still missing a
 * key renders its own "Föreslå facit" fix, and two or more also render the
 * single "Föreslå facit för alla" request.
 */
const hasAiControl = computed(() => missingKeys.value > 0);
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
    <p
      v-if="!canUseAi && hasAiControl"
      :id="aiNoteId"
      class="xw-hint"
      data-test="exam-workspace-blocker-ai-note"
    >
      {{ AI_ADMIN_ONLY_NOTE }}
    </p>
    <button
      v-if="missingKeys > 1"
      type="button"
      class="xw-mblock__fix xw-mblock__all"
      :disabled="fixDisabled || suggestBusy || !canUseAi"
      :title="!canUseAi ? AI_ADMIN_ONLY_NOTE : undefined"
      :aria-describedby="!canUseAi ? aiNoteId : undefined"
      data-test="exam-workspace-blocker-suggest-all"
      @click="emit('suggestAll')"
    >
      Föreslå facit för alla ({{ missingKeys }})
    </button>
    <div
      v-for="blocker in blockers"
      :key="blocker.itemId ?? blocker.reason"
      class="xw-mblock__row"
    >
      <button
        type="button"
        class="xw-mblock__go"
        :data-test="`exam-workspace-blocker-${blocker.itemId ?? 'title'}`"
        @click="emit('goto', blocker)"
      >
        {{ blocker.label === null ? blocker.problem : `Fråga ${blocker.label}: ${blocker.problem}` }}
      </button>
      <button
        v-if="blocker.fix"
        type="button"
        class="xw-mblock__fix"
        :disabled="fixDisabled || (blocker.fix === 'suggest_key' && (suggestBusy || !canUseAi))"
        :title="blocker.fix === 'suggest_key' && !canUseAi ? AI_ADMIN_ONLY_NOTE : undefined"
        :aria-label="`Fråga ${blocker.label}: ${EXAM_WORKSPACE_BLOCKER_FIX_LABELS[blocker.fix]}`"
        :aria-describedby="blocker.fix === 'suggest_key' && !canUseAi ? aiNoteId : undefined"
        :data-test="`exam-workspace-blocker-fix-${blocker.itemId ?? 'title'}`"
        @click="emit('fix', blocker)"
      >
        {{ EXAM_WORKSPACE_BLOCKER_FIX_LABELS[blocker.fix] }}
      </button>
    </div>
  </div>
</template>
