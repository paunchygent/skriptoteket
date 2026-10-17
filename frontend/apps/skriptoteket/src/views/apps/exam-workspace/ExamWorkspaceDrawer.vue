<script setup lang="ts">
/**
 * Exam workspace drawer frame.
 *
 * Domain purpose:
 *   The one frame for Öppna, Exportera and Provets uppgifter. On a desktop
 *   it docks as a third column and leaves focus where it was; on a tablet
 *   it floats over the editor's right edge, takes focus and closes with
 *   Escape from inside; on a phone it covers the screen as a modal dialog
 *   with Tillbaka in its head, keeps Tab inside and closes with Escape.
 *   Focus returns to the button that opened it.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; the drawer bodies fill its slot.
 *   - Keyboard and focus handling comes from `useDialogFocus`.
 */

import { computed, ref, useId } from "vue";

import { UiGlyph } from "../../../components/ui";
import { useDialogFocus } from "../../../composables/useDialogFocus";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";

const props = defineProps<{
  title: string;
  layout: ExamWorkspaceLayout;
  /** The header button that opened the drawer, for focus on close. */
  openerSelector: string;
  testId: string;
}>();

const emit = defineEmits<{ close: [] }>();

const frame = ref<HTMLElement | null>(null);
const titleId = useId();
const isPhone = computed(() => props.layout === "phone");

useDialogFocus(frame, {
  modal: () => isPhone.value,
  takesFocus: () => props.layout !== "desktop",
  fallbackFocus: () => document.querySelector<HTMLElement>(props.openerSelector),
  onClose: () => emit("close"),
});
</script>

<template>
  <aside
    ref="frame"
    class="drawer"
    :class="`drawer--${layout}`"
    :role="isPhone ? 'dialog' : 'complementary'"
    :aria-modal="isPhone || undefined"
    :aria-labelledby="titleId"
    :tabindex="layout === 'desktop' ? undefined : -1"
    :data-test="testId"
  >
    <div class="drawer__head">
      <button
        v-if="isPhone"
        type="button"
        class="xw-btn"
        data-test="exam-workspace-drawer-back"
        @click="emit('close')"
      >
        <UiGlyph
          meaning="back"
          :size="20"
        />Tillbaka
      </button>
      <h2
        :id="titleId"
        class="drawer__title"
      >
        {{ title }}
      </h2>
      <button
        v-if="!isPhone"
        type="button"
        class="xw-btn xw-btn--icon xw-btn--ghost"
        :aria-label="`Stäng ${title.toLowerCase()}`"
        title="Stäng"
        data-test="exam-workspace-drawer-close"
        @click="emit('close')"
      >
        <UiGlyph
          meaning="close"
          :size="20"
        />
      </button>
    </div>
    <div class="drawer__body">
      <slot />
    </div>
  </aside>
</template>

<style scoped>
.drawer {
  display: flex; flex-direction: column; min-height: 0; outline: none;
  border-left: 1px solid var(--huleedu-surface-divider); background: var(--huleedu-canvas);
}
.drawer__head {
  display: flex; align-items: center; gap: var(--huleedu-space-3); flex: none; height: 52px;
  padding: 0 var(--huleedu-space-3) 0 var(--huleedu-space-5); border-bottom: 1px solid var(--huleedu-surface-divider);
}
.drawer__title { flex: 1; margin: 0; font-size: var(--huleedu-text-base); font-weight: var(--huleedu-font-semibold); }
.drawer__body {
  display: grid; align-content: start; gap: var(--huleedu-space-6); flex: 1; min-height: 0; overflow-y: auto;
  padding: var(--huleedu-space-5);
}
.drawer--tablet {
  position: absolute; top: 12px; right: 12px; bottom: 12px; z-index: 12; overflow: hidden;
  width: min(var(--xw-drawer, 380px), calc(100% - 24px));
  border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-xl);
  background: var(--huleedu-modal); box-shadow: var(--huleedu-shadow-md);
}
.drawer--phone { position: fixed; inset: 0; z-index: 26; border: 0; background: var(--huleedu-canvas); }
.drawer--phone .drawer__head { height: 56px; padding: 0 var(--huleedu-space-4); }
.drawer--phone .drawer__body { padding: var(--huleedu-space-4); }
</style>
