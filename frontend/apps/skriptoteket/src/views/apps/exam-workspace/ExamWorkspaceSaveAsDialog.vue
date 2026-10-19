<script setup lang="ts">
/**
 * Exam workspace Spara som dialog.
 *
 * Domain purpose:
 *   Save the exam as a new copy under another name in Mina filer. The name
 *   starts as "<namn> (kopia)". The copy opens in place with its own,
 *   empty undo history; the exam it came from keeps its last save. A name
 *   another file already uses is refused at the field.
 *
 * Relationships:
 *   - Opened from the Spara menu by `ExamWorkspaceView`, which saves through
 *     `useExamWorkspaceDocument.saveDocumentAs` and passes back a refusal.
 *   - Keyboard and focus handling comes from `useDialogFocus`.
 */

import { computed, nextTick, ref, useId, watch } from "vue";

import { UiGlyph } from "../../../components/ui";
import { useDialogFocus } from "../../../composables/useDialogFocus";

const props = defineProps<{
  /** The current file name without its extension. */
  currentName: string;
  busy: boolean;
  /** The name the server refused because another file uses it. */
  takenName: string | null;
}>();

const emit = defineEmits<{ save: [name: string]; close: [] }>();

const frame = ref<HTMLElement | null>(null);
const input = ref<HTMLInputElement | null>(null);
const id = useId();
const name = ref(`${props.currentName} (kopia)`);

const taken = computed(() => props.takenName !== null && props.takenName === name.value.trim());
const canSave = computed(() => !props.busy && name.value.trim().length > 0 && !taken.value);

useDialogFocus(frame, {
  modal: () => true,
  takesFocus: () => true,
  initialFocus: () => input.value,
  fallbackFocus: () => document.querySelector<HTMLElement>('[data-test="exam-workspace-save-as-command"]'),
  onClose: () => emit("close"),
});

watch(
  () => props.takenName,
  async (value) => {
    if (value !== null) {
      await nextTick();
      input.value?.focus();
    }
  },
);

function submit(): void {
  if (canSave.value) emit("save", name.value.trim());
}
</script>

<template>
  <div
    class="scrim"
    @click="emit('close')"
  />
  <div
    ref="frame"
    class="dialog"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="`${id}-title`"
    tabindex="-1"
    data-test="exam-workspace-save-as"
  >
    <h2 :id="`${id}-title`">
      Spara som
    </h2>
    <form @submit.prevent="submit">
      <label
        class="xw-label dialog__label"
        :for="`${id}-name`"
      >Namn i Mina filer</label>
      <input
        :id="`${id}-name`"
        ref="input"
        v-model="name"
        class="xw-input"
        :disabled="busy"
        :aria-invalid="taken || undefined"
        :aria-describedby="taken ? `${id}-error` : `${id}-help`"
        data-test="exam-workspace-save-as-name"
      >
      <p
        v-if="taken"
        :id="`${id}-error`"
        class="xw-errline"
        role="alert"
        data-test="exam-workspace-save-as-error"
      >
        <UiGlyph
          meaning="blocker"
          :size="16"
        />Namnet används redan av en annan fil. Välj ett annat namn.
      </p>
      <p
        v-else
        :id="`${id}-help`"
        class="dialog__help"
      >
        Kopian öppnas här och har en egen ångra-historik. Originalet behåller sin senaste sparning.
      </p>
      <div class="dialog__actions">
        <button
          type="button"
          class="xw-btn"
          @click="emit('close')"
        >
          Avbryt
        </button>
        <button
          type="submit"
          class="xw-btn xw-btn--primary"
          :disabled="!canSave"
          data-test="exam-workspace-save-as-submit"
        >
          <UiGlyph
            :meaning="busy ? 'busy' : 'save'"
            :size="20"
            :class="{ 'xw-spin': busy }"
          />Spara kopia
        </button>
      </div>
    </form>
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
.dialog .dialog__label { margin-top: var(--huleedu-space-3); }
.dialog__help { margin: var(--huleedu-space-2) 0 0; font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60); }
.dialog__actions { display: flex; justify-content: flex-end; gap: var(--huleedu-space-2); margin-top: var(--huleedu-space-6); }
@media (max-width: 767px) { .dialog { top: 12vh; } }
</style>
