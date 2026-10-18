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
 *   toolbar, and Ctrl/Cmd+B, I and U toggle marks. The entry never offers gaps
 *   or pictures of its own; a stored one still renders as a fixed atom, so an
 *   edit cannot drop it silently.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceChoiceField` for each choice,
 *     `ExamWorkspaceKategoriseraGrid` for every row and category,
 *     `ExamWorkspaceOrderingField` for each step and
 *     `ExamWorkspaceInstructionEditor` for the part instruction.
 *   - A thin wrapper over `ExamWorkspaceRichTextEditor`, which registers
 *     itself as the shared toolbar's target when the teacher focuses it.
 *   - Emits the whole entry body on any edit; `examWorkspaceItemEdits`
 *     applies it to the document.
 */

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";

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
  }>(),
  {
    disabled: false,
    invalid: false,
    describedBy: undefined,
    borderClass: "border-navy/35",
    variant: "input",
    assetUrls: () => ({}),
  },
);

const emit = defineEmits<{
  updateBody: [body: NativeExamBodyParagraph[]];
  focusEntry: [];
}>();
</script>

<template>
  <ExamWorkspaceRichTextEditor
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
    @update="(next) => emit('updateBody', next)"
    @focus="emit('focusEntry')"
  />
</template>
