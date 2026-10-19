<script setup lang="ts">
/**
 * Exam workspace edit lease notice.
 *
 * Domain purpose:
 *   The read-only state of an exam open in another tab: `Provet kan bara
 *   redigeras i den andra fliken tills du tar över.` with a `Ta över`
 *   action that asks for the edit lease and, once the holder releases or
 *   its lease dies, claims it and reads the newest state. While the
 *   takeover waits the same slot shows `Väntar på att kunna redigera här …`
 *   and the action is disabled. Editing controls stay disabled through the
 *   view while this shows.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` where it already shows notices; the
 *     styling follows the view's notice pattern. The Mac toolbar session owns
 *     toolbar and header looks, so this keeps the view's own notice styling.
 *   - The lease session (`useExamWorkspaceEditing`) owns the read-only state
 *     and the takeover; this is presentation only.
 */

import { computed } from "vue";

const props = defineProps<{ waiting: boolean }>();

const emit = defineEmits<{ takeover: [] }>();

/** The notice text: the takeover wait replaces the lease notice while waiting. */
const noticeText = computed(() =>
  props.waiting
    ? "Väntar på att kunna redigera här …"
    : "Provet kan bara redigeras i den andra fliken tills du tar över.",
);
</script>

<template>
  <div
    class="xw-notice xw-notice--info ws__bar"
    role="status"
    data-test="exam-workspace-edit-lease"
  >
    <span
      class="xw-grow"
      data-test="exam-workspace-edit-lease-text"
    >{{ noticeText }}</span>
    <button
      type="button"
      class="xw-btn xw-btn--compact"
      :disabled="waiting"
      data-test="exam-workspace-edit-lease-takeover"
      @click="emit('takeover')"
    >
      Ta över
    </button>
  </div>
</template>
