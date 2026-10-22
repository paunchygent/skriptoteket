<script setup lang="ts">
/**
 * Exam workspace import status block.
 *
 * Domain purpose:
 *   Show the one import or conversion in flight in the Öppna drawer: its
 *   message (the upload wait, the phase, or the failure), the time spent in
 *   the phase, the question count bar and the retry. The message and the
 *   clock own stable slots, so a longer phase text or a changing count never
 *   moves the clock or changes the row's height; text that does not fit is
 *   cut with an ellipsis and its full text stays in the tooltip.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceOpenDrawer`, which owns the import intents;
 *     the retry is reported back as an event.
 */

import { computed } from "vue";

import { UiGlyph } from "../../../components/ui";

const props = defineProps<{
  message: string;
  /** Time in the current phase as m:ss; null when no phase is known (the slot stays). */
  elapsed: string | null;
  error: string | null;
  progress: { received: number; total: number } | null;
  isConverting: boolean;
  /** The import request is pending: the file is on its way and no status exists yet. */
  isImporting: boolean;
}>();

const emit = defineEmits<{ retry: [] }>();

/** The upload wait and the conversion both keep the busy glyph spinning. */
const isWorking = computed(() => props.isConverting || props.isImporting);
</script>

<template>
  <div
    class="prog"
    role="status"
    aria-live="polite"
    data-test="exam-workspace-conversion-status"
  >
    <div class="prog__line">
      <UiGlyph
        v-if="isWorking"
        meaning="busy"
        :size="16"
        class="xw-spin prog__glyph"
      />
      <span
        class="prog__message"
        :title="message"
        data-test="exam-workspace-conversion-message"
      >{{ message }}</span>
      <span
        class="prog__elapsed xw-muted"
        aria-hidden="true"
        data-test="exam-workspace-conversion-elapsed"
      >{{ elapsed }}</span>
    </div>
    <div
      v-if="progress"
      class="prog__bar"
      role="progressbar"
      aria-label="AI-svar mottagna"
      aria-valuemin="0"
      :aria-valuemax="progress.total"
      :aria-valuenow="progress.received"
      data-test="exam-workspace-conversion-progress"
    >
      <i :style="{ width: `${(100 * progress.received) / progress.total}%` }" />
    </div>
    <button
      v-if="isConverting && error"
      type="button"
      class="xw-btn xw-btn--compact prog__retry"
      data-test="exam-workspace-conversion-retry"
      @click="emit('retry')"
    >
      <UiGlyph
        meaning="retry"
        :size="16"
      />Försök igen
    </button>
    <small
      v-else-if="!isWorking"
      class="xw-muted"
    >Välj provfilen igen för att försöka på nytt.</small>
  </div>
</template>

<style scoped>
/* The single track is minmax(0, 1fr): an implicit auto track would size to the nowrap message's full width and push the clock past the drawer. */
.prog {
  display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--huleedu-space-2); padding: var(--huleedu-space-3) var(--huleedu-space-4);
  border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-surface-content);
  font-size: var(--huleedu-text-sm);
}
.prog__line { display: flex; align-items: center; gap: var(--huleedu-space-2); }
.prog__glyph { flex: none; }
/* The message takes the row's remaining width and never wraps, so the row keeps one line's height. */
.prog__message { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* The clock slot is always in the row and sized for its widest value, so the message never reflows when it appears. */
.prog__elapsed { flex: none; width: 5ch; text-align: right; font-variant-numeric: tabular-nums; }
.prog__bar { height: 6px; overflow: hidden; border-radius: 3px; border: 1px solid var(--huleedu-surface-divider); background: var(--huleedu-navy-02); }
.prog__bar > i { display: block; height: 100%; background: var(--huleedu-action); }
.prog small { font-size: var(--huleedu-text-xs); }
.prog__retry { justify-self: start; }
</style>
