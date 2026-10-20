<script setup lang="ts">
/**
 * Exam workspace shared file notice.
 *
 * Domain purpose:
 *   The one notice above the workspace for a file the app cannot take in:
 *   one sentence stating the outcome, with glyph-only actions (download
 *   the file, remove it, and for a full Mina filer also retry the move).
 *   Action names live in the tooltip and aria-label only; no text sits
 *   inside any button. While an action runs every button is disabled.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceTeacherHost` above the view for a browser
 *     draft Mina filer refused for good, and by the Öppna drawer for a
 *     saved exam in a format the app cannot read; the notice classes and
 *     the leading glyph follow `ExamWorkspaceSignInPrompt`, and the
 *     glyph-only buttons follow the `.xw-tool` pattern in
 *     `ExamWorkspaceQuestionTools`.
 *   - Presentation only: the caller owns the reason, the busy state and
 *     every action.
 */

import { computed } from "vue";

import { UiGlyph } from "../../../components/ui";
import {
  EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_VAULT_FULL_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_RETRY_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVE_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY,
} from "./examWorkspaceFileNoticeCopy";

const props = defineProps<{
  reason: "guest_permanent" | "guest_vault_full" | "saved_unreadable";
  busy: boolean;
}>();

const emit = defineEmits<{
  download: [];
  remove: [];
  retry: [];
}>();

/** The notice text: a full Mina filer explains itself and names the retry. */
const noticeText = computed(() =>
  props.reason === "guest_vault_full"
    ? EXAM_WORKSPACE_FILE_NOTICE_GUEST_VAULT_FULL_COPY
    : props.reason === "saved_unreadable"
      ? EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY
      : EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
);

/** The remove name: a saved exam is removed from Mina filer, a draft from the browser. */
const removeName = computed(() =>
  props.reason === "saved_unreadable"
    ? EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVE_NAME
    : EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME,
);
</script>

<template>
  <div
    class="xw-notice notice xw-notice--info"
    role="status"
    data-test="exam-workspace-file-notice"
  >
    <UiGlyph
      meaning="info"
      :size="16"
    />
    <span
      class="xw-grow"
      data-test="exam-workspace-file-notice-text"
    >{{ noticeText }}</span>
    <button
      v-if="props.reason === 'guest_vault_full'"
      type="button"
      class="xw-tool"
      :disabled="props.busy"
      :title="EXAM_WORKSPACE_FILE_NOTICE_RETRY_NAME"
      :aria-label="EXAM_WORKSPACE_FILE_NOTICE_RETRY_NAME"
      data-test="exam-workspace-file-notice-retry"
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
      :title="EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME"
      :aria-label="EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME"
      data-test="exam-workspace-file-notice-download"
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
      :title="removeName"
      :aria-label="removeName"
      data-test="exam-workspace-file-notice-remove"
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
