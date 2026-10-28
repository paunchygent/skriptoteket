<script setup lang="ts">
/**
 * Exam workspace question AI group.
 *
 * Domain purpose:
 *   The question-text toolbar's last group (TASK-SKRIPT-40-04-26 D2-D6):
 *   Föreslå facit for this one question, Ta bort AI-facit, and Byt till
 *   [typ] while the labeler suggests another type. Its own separator is its
 *   first child, so a group pinned to the bar's right edge keeps that edge.
 *   The states come from `useExamWorkspaceQuestionAiControls`, the one
 *   computed state the ⋮ Fler åtgärder menu rows also read: the suggestion is
 *   offered only on a keyless question and reads Föreslå nytt facit for its one
 *   retry (D4), the daily limit disables it with the door's own note as `title`
 *   and `aria-description`, and the undo is enabled while an AI key can be
 *   undone. Byt till disables while a suggestion runs, and a guest gets no
 *   group at all. The band composition (which parts show a word) is the
 *   workspace stylesheet's, not this component's.
 *
 * Relationships:
 *   - Rendered in the `end` slot of `ExamWorkspaceMarkToolbar`, filled by
 *     `ExamWorkspaceQuestionEditor` through the body editor or the Kort svar
 *     field, with the controls that editor computed.
 *   - Asks for nothing itself: it emits `suggest`, `undo` and `convert` and
 *     the editor routes them to the workspace harness, the `undoAiKey` emit
 *     and the `changeType` emit.
 */

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { AI_KEY_UNDO_GLYPH } from "./examWorkspaceQuestionAi";
import type { QuestionAiControls } from "./examWorkspaceQuestionAi";

const props = defineProps<{
  controls: QuestionAiControls;
}>();

const emit = defineEmits<{
  suggest: [];
  undo: [];
  convert: [kind: NativeExamItemKind];
}>();
</script>

<template>
  <div
    v-if="props.controls.suggest !== null || props.controls.undo !== null || props.controls.convert !== null"
    class="xw-tools qai"
    role="group"
    aria-label="AI-förslag för frågan"
  >
    <span
      class="xw-toolsep"
      aria-hidden="true"
    />
    <button
      v-if="props.controls.suggest !== null"
      type="button"
      class="xw-tool"
      :disabled="!props.controls.suggest.enabled"
      :aria-label="props.controls.suggest.label"
      :title="props.controls.suggest.title"
      :aria-description="props.controls.suggest.description ?? undefined"
      data-test="exam-workspace-ai-suggest"
      @click="emit('suggest')"
    >
      <UiGlyph
        :meaning="props.controls.suggest.busy ? 'busy' : 'ai-assist'"
        :size="16"
        class="xw-ai"
        :class="{ 'xw-spin': props.controls.suggest.busy }"
      />
    </button>
    <button
      v-if="props.controls.undo !== null"
      type="button"
      class="xw-tool"
      :disabled="!props.controls.undo.enabled"
      :aria-label="props.controls.undo.label"
      :title="props.controls.undo.title"
      data-test="exam-workspace-ai-undo"
      @click="emit('undo')"
    >
      <UiGlyph
        :meaning="AI_KEY_UNDO_GLYPH"
        :size="16"
        class="xw-ai"
      />
    </button>
    <button
      v-if="props.controls.convert !== null"
      type="button"
      class="xw-tool xw-tool--word qai__type"
      :disabled="!props.controls.convert.enabled"
      :aria-label="props.controls.convert.label"
      :title="props.controls.convert.title"
      data-test="exam-workspace-suggested-type"
      @click="emit('convert', props.controls.convert.kind)"
    >
      <UiGlyph
        meaning="convert-type"
        :size="16"
        class="xw-ai"
      />
      <span class="qai__name">{{ props.controls.convert.typeName }}</span>
    </button>
  </div>
</template>
