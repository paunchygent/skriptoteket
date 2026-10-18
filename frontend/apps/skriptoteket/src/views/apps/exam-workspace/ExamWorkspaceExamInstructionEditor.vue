<script setup lang="ts">
/**
 * Exam workspace exam instruction editor.
 *
 * Domain purpose:
 *   Edit the instruction printed before the exam's first question on the
 *   shared rich-text editor with the formatting toolbar, like a part
 *   instruction. An emptied instruction saves as empty and is not printed;
 *   the question list then offers "Lägg till instruktioner" again.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceEditorPane` when the list's "Instruktioner"
 *     entry is selected; emits the whole body on every edit, which the pane
 *     stores through `setExamInstructions`.
 */

import { computed } from "vue";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel } from "./examWorkspaceRichTextTarget";
import type { BodyMark } from "./examWorkspaceBodyMarks";

defineProps<{
  instructions: NativeExamBodyParagraph[];
  disabled: boolean;
  /** Picture URLs by asset id, so a declared picture in the instruction renders. */
  assetUrls?: Record<string, string>;
}>();

const emit = defineEmits<{ updateInstructions: [body: NativeExamBodyParagraph[], structural: boolean] }>();

const targets = provideRichTextTargetRegistry();
const activeMarks = computed(() => targets.active.value?.marks.value ?? []);
const activeHeading = computed(() => targets.active.value?.headingLevel() ?? null);

function toggleMark(mark: BodyMark): void {
  targets.active.value?.toggleMark(mark);
}

function toggleHeading(level: RichTextHeadingLevel): void {
  targets.active.value?.toggleHeading(level);
}
</script>

<template>
  <section
    class="eie"
    aria-labelledby="exam-workspace-exam-instructions-title"
    data-test="exam-workspace-exam-instruction-editor"
  >
    <h1
      id="exam-workspace-exam-instructions-title"
      class="eie__title"
    >
      Instruktioner
    </h1>
    <p class="eie__hint">
      Texten skrivs ut före den första frågan.
    </p>
    <div class="xw-rich">
      <ExamWorkspaceMarkToolbar
        class="xw-rich__bar"
        :active-marks="activeMarks"
        :active-heading="activeHeading"
        :disabled="disabled"
        show-headings
        @toggle-mark="toggleMark"
        @toggle-heading="toggleHeading"
      />
      <ExamWorkspaceRichTextEntry
        class="xw-rich__body"
        :body="instructions"
        :disabled="disabled"
        label="Instruktioner"
        test-id="exam-workspace-exam-instruction-text"
        variant="paragraph"
        :asset-urls="assetUrls"
        @update-body="(body, structural) => emit('updateInstructions', body, structural)"
      />
    </div>
  </section>
</template>

<style scoped>
.eie { display: flex; flex-direction: column; min-width: 0; }
.eie__title { margin: 0; font-size: var(--huleedu-text-lg); font-weight: var(--huleedu-font-semibold); }
.eie__hint { margin: var(--huleedu-space-1) 0 var(--huleedu-space-4); font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-70); }
</style>
