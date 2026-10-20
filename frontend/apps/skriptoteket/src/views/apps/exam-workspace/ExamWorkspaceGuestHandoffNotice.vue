<script setup lang="ts">
/**
 * Exam workspace guest handoff notice.
 *
 * Domain purpose:
 *   The notice a signed-in teacher sees above the workspace when Mina filer
 *   refused the browser draft for good: one sentence stating the outcome,
 *   with glyph-only actions (download the draft as a file, remove it from
 *   the browser, and for a full Mina filer also retry the move). Action
 *   names live in the tooltip and aria-label only; no text sits inside any
 *   button. While an action runs every button is disabled.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceTeacherHost` above the view, like the guest
 *     host's notices; the notice classes and the leading glyph follow
 *     `ExamWorkspaceSignInPrompt`, and the glyph-only buttons follow the
 *     `.xw-tool` pattern in `ExamWorkspaceQuestionTools`.
 *   - Presentation only: `useExamWorkspaceGuestHandoffController` owns the
 *     reason, the busy state and every action.
 */

import { computed } from "vue";

import { UiGlyph } from "../../../components/ui";
import {
  EXAM_WORKSPACE_GUEST_HANDOFF_DOWNLOAD_NAME,
  EXAM_WORKSPACE_GUEST_HANDOFF_PERMANENT_COPY,
  EXAM_WORKSPACE_GUEST_HANDOFF_REMOVE_NAME,
  EXAM_WORKSPACE_GUEST_HANDOFF_RETRY_NAME,
  EXAM_WORKSPACE_GUEST_HANDOFF_VAULT_FULL_COPY,
} from "./examWorkspaceGuestHandoffCopy";

const props = defineProps<{
  reason: "permanent" | "vault_full";
  busy: boolean;
}>();

const emit = defineEmits<{
  download: [];
  remove: [];
  retry: [];
}>();

/** The notice text: a full Mina filer explains itself and names the retry. */
const noticeText = computed(() =>
  props.reason === "vault_full"
    ? EXAM_WORKSPACE_GUEST_HANDOFF_VAULT_FULL_COPY
    : EXAM_WORKSPACE_GUEST_HANDOFF_PERMANENT_COPY,
);
</script>

<template>
  <div
    class="xw-notice notice xw-notice--info"
    role="status"
    data-test="exam-workspace-guest-handoff-notice"
  >
    <UiGlyph
      meaning="info"
      :size="16"
    />
    <span
      class="xw-grow"
      data-test="exam-workspace-guest-handoff-notice-text"
    >{{ noticeText }}</span>
    <button
      v-if="props.reason === 'vault_full'"
      type="button"
      class="xw-tool"
      :disabled="props.busy"
      :title="EXAM_WORKSPACE_GUEST_HANDOFF_RETRY_NAME"
      :aria-label="EXAM_WORKSPACE_GUEST_HANDOFF_RETRY_NAME"
      data-test="exam-workspace-guest-handoff-retry"
      @click="emit('retry')"
    >
      <UiGlyph
        meaning="retry"
        :size="16"
      />
    </button>
    <button
      type="button"
      class="xw-tool"
      :disabled="props.busy"
      :title="EXAM_WORKSPACE_GUEST_HANDOFF_DOWNLOAD_NAME"
      :aria-label="EXAM_WORKSPACE_GUEST_HANDOFF_DOWNLOAD_NAME"
      data-test="exam-workspace-guest-handoff-download"
      @click="emit('download')"
    >
      <UiGlyph
        meaning="download"
        :size="16"
      />
    </button>
    <button
      type="button"
      class="xw-tool"
      :disabled="props.busy"
      :title="EXAM_WORKSPACE_GUEST_HANDOFF_REMOVE_NAME"
      :aria-label="EXAM_WORKSPACE_GUEST_HANDOFF_REMOVE_NAME"
      data-test="exam-workspace-guest-handoff-remove"
      @click="emit('remove')"
    >
      <UiGlyph
        meaning="delete"
        :size="16"
      />
    </button>
  </div>
</template>

<style scoped>
.notice { margin-bottom: var(--huleedu-space-3); }
</style>
