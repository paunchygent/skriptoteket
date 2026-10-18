<script setup lang="ts">
/**
 * Exam workspace phone question strip.
 *
 * Domain purpose:
 *   On a phone the question list is a layer, so this strip under the header
 *   moves between questions: previous, "Fråga 3" with its state, which opens
 *   the list, and next. The selected question's Import and review check sit
 *   beside it, because the question header has no room for them.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` below 768 px; the tools come in
 *     through the default slot (`ExamWorkspaceQuestionTools`).
 */

import { UiGlyph } from "../../../components/ui";

defineProps<{
  label: string | null;
  /** Names the selected entry when it has no question number, e.g. the exam instruction. */
  heading?: string | null;
  /** The selected entry's state glyph: an instruction, converting, ok or warn. */
  state: "instruction" | "converting" | "ok" | "warn" | null;
  canPrevious: boolean;
  canNext: boolean;
  listOpen: boolean;
}>();

const emit = defineEmits<{ previous: []; next: []; openList: [] }>();
</script>

<template>
  <div
    class="strip"
    data-test="exam-workspace-phone-strip"
  >
    <div class="strip__nav">
      <button
        type="button"
        :disabled="!canPrevious"
        aria-label="Föregående fråga"
        data-test="exam-workspace-phone-previous"
        @click="emit('previous')"
      >
        <UiGlyph
          meaning="previous"
          :size="20"
        />
      </button>
      <button
        type="button"
        class="strip__pos"
        aria-haspopup="listbox"
        :aria-expanded="listOpen"
        data-test="exam-workspace-phone-list"
        @click="emit('openList')"
      >
        <UiGlyph
          v-if="state === 'instruction'"
          meaning="instruction"
          :size="16"
        />
        <UiGlyph
          v-else-if="state === 'converting'"
          meaning="busy"
          :size="16"
          class="xw-spin"
        />
        <span
          v-else-if="state === 'ok'"
          class="xw-ok"
          role="img"
          aria-label="Granskad"
        ><UiGlyph
          meaning="status-success"
          :size="16"
        /></span>
        <span
          v-else-if="state === 'warn'"
          class="xw-warn"
          role="img"
          aria-label="Behöver granskas"
        ><UiGlyph
          meaning="status-warning"
          :size="16"
        /></span>
        <span class="strip__label">{{ heading ?? (label ? `Fråga ${label}` : "Inget prov") }}</span>
        <UiGlyph
          meaning="open-list"
          :size="16"
          class="strip__chevron"
        />
      </button>
      <button
        type="button"
        :disabled="!canNext"
        aria-label="Nästa fråga"
        data-test="exam-workspace-phone-next"
        @click="emit('next')"
      >
        <UiGlyph
          meaning="next"
          :size="20"
        />
      </button>
    </div>
    <div class="strip__tools">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.strip {
  display: flex; align-items: center; gap: var(--huleedu-space-2); flex: none;
  padding: var(--huleedu-space-2) var(--huleedu-space-4); border-bottom: 1px solid var(--huleedu-surface-divider);
}
.strip__nav {
  flex: 1; min-width: 0; display: grid; grid-template-columns: 44px minmax(0, 1fr) 44px; height: 44px;
  border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-md); background: var(--huleedu-surface-content);
}
.strip__nav > button {
  all: unset; box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center; gap: var(--huleedu-space-2);
  min-width: 0; overflow: hidden; white-space: nowrap; cursor: pointer; font-size: var(--huleedu-text-sm);
}
.strip__nav > button:disabled { cursor: default; color: var(--huleedu-navy-30); }
.strip__nav > button:focus-visible { outline: 2px solid var(--huleedu-action-40); outline-offset: -2px; }
.strip__nav > * + * { border-left: 1px solid var(--huleedu-panel-border); }
.strip__label { overflow: hidden; text-overflow: ellipsis; }
.strip__chevron { flex: none; color: var(--huleedu-navy-60); }
.strip__tools { display: flex; gap: var(--huleedu-space-2); flex: none; }
</style>
