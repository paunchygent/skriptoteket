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

import { computed, ref } from "vue";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceInlineNotice from "./ExamWorkspaceInlineNotice.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";
import { useExamWorkspacePictureControl } from "./examWorkspacePictureService";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel } from "./examWorkspaceRichTextTarget";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

defineProps<{
  instructions: NativeExamBodyParagraph[];
  disabled: boolean;
  /** Picture URLs by asset id, so a declared picture in the instruction renders. */
  assetUrls?: Record<string, string>;
  /** The refused picture file, shown until the teacher closes it or moves on. */
  notice?: ExamWorkspaceNotice | null;
}>();

const emit = defineEmits<{
  updateInstructions: [body: NativeExamBodyParagraph[], structural: boolean];
  dismissNotice: [];
}>();

const targets = provideRichTextTargetRegistry();
const activeMarks = computed(() => targets.active.value?.marks.value ?? []);
const activeHeading = computed(() => targets.active.value?.headingLevel() ?? null);

/** The exam instruction's own entry: the picture fallback when no selected surface takes pictures. */
const entry = ref<InstanceType<typeof ExamWorkspaceRichTextEntry> | null>(null);


function toggleMark(mark: BodyMark): void {
  targets.active.value?.toggleMark(mark);
}

function toggleHeading(level: RichTextHeadingLevel): void {
  targets.active.value?.toggleHeading(level);
}

/** The picture button: its state and where a chosen file goes. */
const {
  enabled: picturesEnabled,
  selected: pictureSelected,
  busy: pictureBusy,
  add: handleAddPicture,
} = useExamWorkspacePictureControl(
  () => targets.active.value,
  () => entry.value,
);
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
    <ExamWorkspaceInlineNotice
      v-if="notice"
      :notice="notice"
      @dismiss="emit('dismissNotice')"
    />
    <div class="xw-rich">
      <ExamWorkspaceMarkToolbar
        class="xw-rich__bar"
        :active-marks="activeMarks"
        :active-heading="activeHeading"
        :disabled="disabled"
        show-headings
        :show-picture="picturesEnabled"
        :picture-selected="pictureSelected"
        :picture-busy="pictureBusy"
        @toggle-mark="toggleMark"
        @toggle-heading="toggleHeading"
        @add-picture="handleAddPicture"
      />
      <ExamWorkspaceRichTextEntry
        ref="entry"
        class="xw-rich__body"
        :body="instructions"
        :disabled="disabled"
        label="Instruktioner"
        test-id="exam-workspace-exam-instruction-text"
        variant="paragraph"
        :asset-urls="assetUrls"
        :pictures="picturesEnabled"
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
