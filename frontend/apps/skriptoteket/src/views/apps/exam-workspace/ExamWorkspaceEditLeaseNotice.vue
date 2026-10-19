<script setup lang="ts">
/**
 * Exam workspace edit lease notice.
 *
 * Domain purpose:
 *   The read-only state of an exam open in another tab: `Öppet i en annan
 *   flik` with a `Ta över` action that asks for the edit lease and, once the
 *   holder releases or its lease dies, claims it and reads the newest state.
 *   Editing controls stay disabled through the view while this shows.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` where it already shows notices; the
 *     styling follows the view's notice pattern. The Mac toolbar session owns
 *     toolbar and header looks, so this keeps the view's own notice styling.
 *   - The lease session (`useExamWorkspaceEditing`) owns the read-only state
 *     and the takeover; this is presentation only.
 */

defineProps<{ waiting: boolean }>();

const emit = defineEmits<{ takeover: [] }>();
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
    >Öppet i en annan flik</span>
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
