<script setup lang="ts">
/**
 * Exam workspace gap automatic answers.
 *
 * Domain purpose:
 *   Show the answers the conversion wrote for a gap as removable chips
 *   marked "automatisk" with no AI glyph. Removing one emits the value;
 *   the owner removes the record.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceGapPopover` for a text gap and by the Kort
 *     svar "Svar" field, both of which keep the v-if on non-empty values.
 */

import { IconX } from "../../../components/icons";

const props = defineProps<{
  values: string[];
  disabled?: boolean;
}>();

const emit = defineEmits<{
  remove: [value: string];
}>();

function handleRemove(value: string): void {
  if (props.disabled) {
    return;
  }
  emit("remove", value);
}
</script>

<template>
  <div
    class="grid min-w-0 gap-1.5"
    data-test="exam-workspace-gap-automatic-values"
  >
    <p class="text-[11px] font-semibold leading-snug text-navy/80">
      Automatiska svar
    </p>
    <ul class="flex flex-wrap gap-1.5">
      <li
        v-for="value in values"
        :key="value"
        class="inline-flex min-h-7 items-center gap-1.5 border border-navy/35 bg-panel-muted px-2 text-xs text-navy"
        :data-test="`exam-workspace-gap-automatic-${value}`"
        :data-value="value"
      >
        <span class="font-semibold">{{ value }}</span>
        <span class="text-[11px] leading-none text-navy/65">automatisk</span>
        <button
          type="button"
          class="inline-flex h-11 w-11 shrink-0 items-center justify-center border border-navy/35 bg-panel text-navy hover:bg-canvas focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action/40 sm:h-7 sm:w-7"
          :disabled="disabled"
          :aria-label="`Ta bort automatisk stavning: ${value}`"
          :title="`Ta bort automatisk stavning: ${value}`"
          :data-test="`exam-workspace-gap-automatic-remove-${value}`"
          @click="handleRemove(value)"
        >
          <IconX :size="14" />
        </button>
      </li>
    </ul>
  </div>
</template>
