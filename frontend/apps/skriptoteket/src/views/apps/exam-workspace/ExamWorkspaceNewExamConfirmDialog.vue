<script setup lang="ts">
/**
 * Exam workspace Nytt prov confirm dialog (TASK-SKRIPT-40-04-21).
 *
 * Domain purpose:
 *   A guest whose open browser draft has content confirms replacing it with
 *   a new untitled exam: the draft is kept nowhere else, so Ersätt discards
 *   it. Avbryt keeps the draft unchanged.
 *
 * Relationships:
 *   - Opened from "Nytt prov" by `ExamWorkspaceView` through
 *     `useExamWorkspaceNewExam`, which owns the confirm state; the keyboard
 *     and focus handling comes from `useDialogFocus`.
 */

import { ref, useId } from "vue";

import { useDialogFocus } from "../../../composables/useDialogFocus";

const emit = defineEmits<{ replace: []; cancel: [] }>();

const frame = ref<HTMLElement | null>(null);
const cancelButton = ref<HTMLButtonElement | null>(null);
const id = useId();

useDialogFocus(frame, {
  modal: () => true,
  takesFocus: () => true,
  initialFocus: () => cancelButton.value,
  fallbackFocus: () => document.querySelector<HTMLElement>('[data-test="exam-workspace-new-exam"]'),
  onClose: () => emit("cancel"),
});
</script>

<template>
  <div
    class="scrim"
    @click="emit('cancel')"
  />
  <div
    ref="frame"
    class="dialog"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="`${id}-title`"
    :aria-describedby="`${id}-body`"
    tabindex="-1"
    data-test="exam-workspace-new-exam-confirm"
  >
    <h2 :id="`${id}-title`">
      Nytt prov
    </h2>
    <p
      :id="`${id}-body`"
      class="dialog__body"
    >
      Det öppna provet ersätts av ett nytt. Exportera det först om du vill behålla det.
    </p>
    <div class="dialog__actions">
      <button
        ref="cancelButton"
        type="button"
        class="xw-btn"
        data-test="exam-workspace-new-exam-confirm-cancel"
        @click="emit('cancel')"
      >
        Avbryt
      </button>
      <button
        type="button"
        class="xw-btn xw-btn--primary"
        data-test="exam-workspace-new-exam-confirm-replace"
        @click="emit('replace')"
      >
        Ersätt
      </button>
    </div>
  </div>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; z-index: 45; background: rgba(8, 43, 76, 0.32); }
.dialog {
  position: fixed; z-index: 46; left: 50%; top: 18vh; transform: translateX(-50%); outline: none;
  width: min(480px, calc(100vw - 32px)); padding: var(--huleedu-space-6);
  border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-xl);
  background: var(--huleedu-modal); box-shadow: var(--huleedu-shadow-md);
}
.dialog h2 { margin: 0 0 var(--huleedu-space-2); font-size: var(--huleedu-text-xl); font-weight: var(--huleedu-font-semibold); }
.dialog__body { margin: var(--huleedu-space-3) 0 0; font-size: var(--huleedu-text-sm); }
.dialog__actions { display: flex; justify-content: flex-end; gap: var(--huleedu-space-2); margin-top: var(--huleedu-space-6); }
@media (max-width: 767px) { .dialog { top: 12vh; } }
</style>
