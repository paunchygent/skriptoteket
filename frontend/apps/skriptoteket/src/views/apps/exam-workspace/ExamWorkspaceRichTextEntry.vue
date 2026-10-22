<script setup lang="ts">
/**
 * Exam workspace rich text entry.
 *
 * Domain purpose:
 *   Edit one choice option, matching entry, ordering step or part instruction
 *   as rich text on the shared exam editor: the whole entry is one editable
 *   document that edits like a word processor. A selection across paragraphs
 *   deletes, Backspace at a paragraph start merges, Enter starts a paragraph
 *   and Shift+Enter breaks the line. Clearing the text is allowed: the entry
 *   emits the empty body and keeps it; the item's export blockers, not the
 *   editor, say that an option, entry or step is missing its text. The five
 *   kept marks and the heading glyphs act through the item editor's shared
 *   toolbar, and Ctrl/Cmd+B, I and U toggle marks. The entry offers no gap
 *   tool of its own, and pictures only when its `pictures` prop asks for them:
 *   then a dropped or pasted file goes to the picture service with this entry
 *   as the target. A stored gap or picture always renders as a fixed atom, so
 *   an edit cannot drop it silently.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceChoiceField` for each choice,
 *     `ExamWorkspaceKategoriseraGrid` for every row and category,
 *     `ExamWorkspaceOrderingField` for each step and
 *     `ExamWorkspaceInstructionEditor` for the part instruction.
 *   - A thin wrapper over `ExamWorkspaceRichTextEditor`, which registers
 *     itself as the shared toolbar's target when the teacher focuses it; the
 *     entry re-exposes that target and its focus for a host that places a
 *     chosen picture on its own entry.
 *   - Emits the whole entry body on any edit; `examWorkspaceItemEdits`
 *     applies it to the document.
 */

import { ref } from "vue";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import type { RichTextTarget } from "./examWorkspaceRichTextTarget";

withDefaults(
  defineProps<{
    body: NativeExamBodyParagraph[];
    disabled?: boolean;
    label: string;
    /** `data-test` of the editing surface. */
    testId: string;
    invalid?: boolean;
    describedBy?: string;
    /** The input border colour, so an empty or correct entry can mark itself. */
    borderClass?: string;
    /** `paragraph` flows the text inside a surrounding bordered editor box instead of its own input border. */
    variant?: "paragraph" | "input";
    /** Picture URLs by asset id; an unmapped picture keeps its "Bild" placeholder. */
    assetUrls?: Record<string, string>;
    /** While true, the entry takes dropped and pasted pictures. */
    pictures?: boolean;
  }>(),
  {
    disabled: false,
    invalid: false,
    describedBy: undefined,
    borderClass: "border-navy/35",
    variant: "input",
    assetUrls: () => ({}),
    pictures: false,
  },
);

const emit = defineEmits<{
  updateBody: [body: NativeExamBodyParagraph[], structural: boolean];
  focusEntry: [];
}>();

const editor = ref<InstanceType<typeof ExamWorkspaceRichTextEditor> | null>(null);

defineExpose({
  /** The entry's own rich target, so the host can place a chosen picture on it. */
  get target(): RichTextTarget | undefined {
    return editor.value?.target;
  },
  focus(): void {
    editor.value?.focus();
  },
});
</script>

<template>
  <ExamWorkspaceRichTextEditor
    ref="editor"
    :body="body"
    :disabled="disabled"
    :label="label"
    :test-id="testId"
    :invalid="invalid"
    :described-by="describedBy"
    :border-class="borderClass"
    :variant="variant === 'input' ? 'compact' : 'field'"
    :asset-urls="assetUrls"
    :gaps-interactive="false"
    :pictures="pictures"
    @update="(next, structural) => emit('updateBody', next, structural)"
    @focus="emit('focusEntry')"
  />
</template>
