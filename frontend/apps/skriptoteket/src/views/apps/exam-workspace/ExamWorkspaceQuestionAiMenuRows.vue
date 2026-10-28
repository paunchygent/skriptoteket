<script setup lang="ts">
/**
 * Exam workspace question AI menu rows.
 *
 * Domain purpose:
 *   The question's three AI controls as the words of ⋮ Fler åtgärder, above
 *   the built rows and followed by one separator: Föreslå facit, Ta bort
 *   AI-facit and Byt till [typ] (TASK-SKRIPT-40-04-26 D7, D8). A menu
 *   row has no tooltip and touch has no hover, so a phone or touch device
 *   reads the controls as words here instead of as the question-text
 *   toolbar's glyph tools. The rows render whenever the question has that
 *   control, whatever the band; the stylesheet decides where they show.
 *   A disabled row keeps its reason as `aria-disabled` and the built hint,
 *   and a click does nothing; an enabled row emits its intent, and the head
 *   closes the menu. No control means no row and no separator.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionHead` inside its ⋮ Fler åtgärder
 *     menu; the states are the same `QuestionAiControls` the toolbar group
 *     reads and the editor computes once, so the two cannot disagree.
 *   - `examWorkspaceQuestionAi` owns which control exists and why.
 */

import { computed } from "vue";

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import type { UiGlyphMeaning } from "../../../components/ui";
import { AI_KEY_UNDO_GLYPH } from "./examWorkspaceQuestionAi";
import type { QuestionAiControls } from "./examWorkspaceQuestionAi";

const props = defineProps<{ controls: QuestionAiControls }>();

const emit = defineEmits<{
  suggest: [];
  undo: [];
  convert: [kind: NativeExamItemKind];
}>();

/** Which of the three AI controls a menu row stands for. */
type AiMenuAction = "suggest" | "undo" | "convert";

/** One AI row of ⋮ Fler åtgärder: the control's word, glyph and intent. */
type AiMenuRow = {
  action: AiMenuAction;
  enabled: boolean;
  label: string;
  /** A short reason the row is disabled, or null. */
  hint: string | null;
  /** The editable suggestion's own sentence, read as `aria-description`. */
  description: string | null;
  glyph: UiGlyphMeaning;
  /** The glyph spins while a suggestion runs. */
  busy: boolean;
  /** The type a convert row asks for; null on the other rows. */
  kind: NativeExamItemKind | null;
  testId: string;
};

/** The AI rows the editor's controls call for, in toolbar order, each null control left out. */
const aiRows = computed<AiMenuRow[]>(() => {
  const rows: AiMenuRow[] = [];
  const { suggest, undo, convert } = props.controls;
  if (suggest !== null) {
    rows.push({
      action: "suggest",
      busy: suggest.busy,
      description: suggest.description,
      enabled: suggest.enabled,
      glyph: suggest.busy ? "busy" : "ai-assist",
      hint: suggest.hint,
      kind: null,
      label: suggest.label,
      testId: "exam-workspace-more-ai-suggest",
    });
  }
  if (undo !== null) {
    rows.push({
      action: "undo",
      busy: false,
      description: null,
      enabled: undo.enabled,
      glyph: AI_KEY_UNDO_GLYPH,
      hint: undo.hint,
      kind: null,
      label: undo.label,
      testId: "exam-workspace-more-ai-undo",
    });
  }
  if (convert !== null) {
    rows.push({
      action: "convert",
      busy: false,
      description: null,
      enabled: convert.enabled,
      glyph: "convert-type",
      hint: null,
      kind: convert.kind,
      label: convert.label,
      testId: "exam-workspace-more-ai-convert",
    });
  }
  return rows;
});

/** Emit the row's intent; a disabled row does nothing. */
function chooseAi(row: AiMenuRow): void {
  if (!row.enabled) {
    return;
  }
  if (row.action === "suggest") {
    emit("suggest");
  } else if (row.action === "undo") {
    emit("undo");
  } else if (row.kind !== null) {
    emit("convert", row.kind);
  }
}
</script>

<template>
  <template v-if="aiRows.length > 0">
    <button
      v-for="row in aiRows"
      :key="row.action"
      type="button"
      class="xw-mi qai-mi"
      role="menuitem"
      :aria-disabled="!row.enabled || undefined"
      :aria-description="row.description ?? undefined"
      :data-test="row.testId"
      @click="chooseAi(row)"
    >
      <UiGlyph
        :meaning="row.glyph"
        :size="20"
        class="xw-ai"
        :class="{ 'xw-spin': row.busy }"
      /><span class="xw-grow">{{ row.label }}</span><span
        v-if="row.hint"
        class="xw-mi__hint"
      >{{ row.hint }}</span>
    </button>
    <div
      role="separator"
      class="qai-mi-sep"
    />
  </template>
</template>
