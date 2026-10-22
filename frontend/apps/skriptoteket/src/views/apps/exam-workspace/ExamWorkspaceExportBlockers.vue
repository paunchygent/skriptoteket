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
import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import { EXAM_WORKSPACE_BLOCKER_FIX_LABELS } from "./examWorkspaceBlockers";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { GUEST_AI_SIGN_IN } from "./examWorkspaceGuestCopy";
import { useExamWorkspaceSignIn } from "./examWorkspaceSignIn";
import { useExamWorkspaceAiMode } from "./useExamWorkspaceAiMode";
import AiDailyLimitNote from "./AiDailyLimitNote.vue";
import { aiDailyLimitFor } from "../../../composables/aiDailyLimit";

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

const requestSignIn = useExamWorkspaceSignIn();
const aiNoteId = useId();
const limitNoteId = useId();
/** Guest controls stay enabled and ask for sign-in; signed-in controls follow the admin gate. */
const aiMode = useExamWorkspaceAiMode();
const isGuest = computed(() => aiMode.value === "guest");
const adminOnly = computed(() => aiMode.value === "admin_only");
/** The door's daily limit disables the key controls for the page session. */
const { note: aiDailyLimitNote, reached: limitReached } = aiDailyLimitFor("small");
const missingKeys = computed(() => props.blockers.filter((blocker) => blocker.fix === "suggest_key").length);
/**
 * At least one answer-key control is on screen: each question still missing a
 * key renders its own "Föreslå facit" fix, and two or more also render the
 * single "Föreslå facit för alla" request.
 */
const hasAiControl = computed(() => missingKeys.value > 0);

function handleSuggestAll(): void {
  if (limitReached.value) {
    return;
  }
  if (isGuest.value) {
    requestSignIn(GUEST_AI_SIGN_IN);
    return;
  }
  emit("suggestAll");
}

function handleFix(blocker: ExamWorkspaceBlockerEntry): void {
  if (blocker.fix === "suggest_key" && limitReached.value) {
    return;
  }
  if (isGuest.value && blocker.fix === "suggest_key") {
    requestSignIn(GUEST_AI_SIGN_IN);
    return;
  }
  emit("fix", blocker);
}
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
      v-if="adminOnly && hasAiControl"
      :id="aiNoteId"
      class="xw-hint"
    >
      {{ AI_ADMIN_ONLY_NOTE }}
    </p>
    <AiDailyLimitNote
      v-if="limitReached && hasAiControl"
      :id="limitNoteId"
    />
    <button
      v-if="missingKeys > 1"
      type="button"
      class="xw-mblock__fix xw-mblock__all"
      :disabled="fixDisabled || suggestBusy || adminOnly || limitReached"
      :title="limitReached ? (aiDailyLimitNote ?? undefined) : adminOnly ? AI_ADMIN_ONLY_NOTE : undefined"
      :aria-describedby="limitReached ? limitNoteId : adminOnly ? aiNoteId : undefined"
      data-test="exam-workspace-blocker-suggest-all"
      @click="handleSuggestAll"
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
        :disabled="fixDisabled || (blocker.fix === 'suggest_key' && (suggestBusy || adminOnly || limitReached))"
        :title="blocker.fix === 'suggest_key' && limitReached ? (aiDailyLimitNote ?? undefined) : blocker.fix === 'suggest_key' && adminOnly ? AI_ADMIN_ONLY_NOTE : undefined"
        :aria-label="`Fråga ${blocker.label}: ${EXAM_WORKSPACE_BLOCKER_FIX_LABELS[blocker.fix]}`"
        :aria-describedby="blocker.fix === 'suggest_key' && limitReached ? limitNoteId : blocker.fix === 'suggest_key' && adminOnly ? aiNoteId : undefined"
        :data-test="`exam-workspace-blocker-fix-${blocker.itemId ?? 'title'}`"
        @click="handleFix(blocker)"
      >
        {{ EXAM_WORKSPACE_BLOCKER_FIX_LABELS[blocker.fix] }}
      </button>
    </div>
  </div>
</template>
