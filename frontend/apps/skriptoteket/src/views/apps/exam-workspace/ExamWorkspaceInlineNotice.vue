<script setup lang="ts">
/**
 * Exam workspace inline notice.
 *
 * Domain purpose:
 *   One sentence in the editor about what the last command did: what a type
 *   change removed, that an instruction went with its last question, or why
 *   a delete was refused. A change the teacher can take back says that the
 *   header's Ångra restores it; a refusal changed nothing. The notice stays
 *   until the teacher closes it or selects another entry (user ruling
 *   2026-10-17: these outcomes are inline, never toasts).
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` and
 *     `ExamWorkspaceInstructionEditor`; the notices come from
 *     `useExamWorkspaceStructure`.
 */

import { computed } from "vue";

import { UiGlyph } from "../../../components/ui";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

const props = defineProps<{ notice: ExamWorkspaceNotice }>();

const emit = defineEmits<{ dismiss: [] }>();

const testId = computed(() => (props.notice.kind === "type" ? "exam-workspace-type-notice" : "exam-workspace-delete-notice"));
</script>

<template>
  <div
    class="xw-notice notice"
    :class="notice.kind === 'refused' ? 'xw-notice--error' : 'xw-notice--info'"
    role="status"
    :data-test="testId"
  >
    <UiGlyph
      :meaning="notice.kind === 'type' ? 'convert-type' : notice.kind === 'refused' ? 'status-warning' : 'info'"
      :size="16"
    />
    <span class="xw-grow">{{ notice.text }}{{ notice.kind === "refused" ? "" : " Ångra återställer det." }}</span>
    <button
      type="button"
      class="xw-rm"
      aria-label="Stäng meddelandet"
      title="Stäng"
      :data-test="`${testId}-close`"
      @click="emit('dismiss')"
    >
      <UiGlyph
        meaning="close"
        :size="16"
      />
    </button>
  </div>
</template>

<style scoped>
.notice { margin-bottom: var(--huleedu-space-3); }
</style>
