<script setup lang="ts">
/**
 * Exam workspace rich text entry.
 *
 * Domain purpose:
 *   Edit one choice option or one matching entry as rich text: every stored
 *   paragraph renders as its own editable line with the five kept marks, in
 *   the compact input surface a choice and a Kategorisera cell need. The
 *   entry never offers gaps or pictures of its own; if a stored body somehow
 *   carries one, it still renders as a fixed atom, so an edit can never drop
 *   it silently. Ctrl/Cmd+B, I and U toggle marks while the teacher edits,
 *   and the item editor's shared toolbar can call this entry's paragraphs
 *   when one of them owns the selection, including the heading glyphs.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceChoiceField` for each choice and by
 *     `ExamWorkspaceKategoriseraGrid` for every row and category.
 *   - Passes the entry's semantic owner down to every paragraph, so the
 *     toolbar target follows the item, choice or Kategorisera entry.
 *   - Emits the whole entry body on any paragraph edit;
 *     `examWorkspaceItemEdits` applies it to the document.
 */

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import ExamWorkspaceBodyParagraph from "./ExamWorkspaceBodyParagraph.vue";
import type { RichTextHeadingLevel } from "./examWorkspaceRichTextTarget";
import type { RichTextSurfaceOwner } from "./useExamWorkspaceRichTextTarget";

const props = withDefaults(
  defineProps<{
    body: NativeExamBodyParagraph[];
    disabled?: boolean;
    label: string;
    testId: string;
    invalid?: boolean;
    describedBy?: string;
    /** The paragraph border colour, so an empty or correct entry can mark itself. */
    borderClass?: string;
    /** `paragraph` flows the text inside a surrounding bordered editor box instead of its own input border. */
    variant?: "paragraph" | "input";
    /** The item, surface and entry this body belongs to; a standalone entry keys on its paragraphs. */
    owner?: RichTextSurfaceOwner;
    /** Picture URLs by asset id; an unmapped picture keeps its "Bild" placeholder. */
    assetUrls?: Record<string, string>;
  }>(),
  {
    disabled: false,
    invalid: false,
    describedBy: undefined,
    borderClass: "border-navy/35",
    variant: "input",
    owner: undefined,
    assetUrls: () => ({}),
  },
);

const emit = defineEmits<{
  updateBody: [body: NativeExamBodyParagraph[]];
  focusEntry: [];
}>();

function handleSegments(paragraphIndex: number, segments: NativeExamBodySegment[]): void {
  emit(
    "updateBody",
    props.body.map((paragraph, index) =>
      index === paragraphIndex ? { ...paragraph, segments } : paragraph,
    ),
  );
}

function handleHeading(paragraphIndex: number, headingLevel: RichTextHeadingLevel | null): void {
  emit(
    "updateBody",
    props.body.map((paragraph, index) =>
      index === paragraphIndex ? { ...paragraph, heading_level: headingLevel } : paragraph,
    ),
  );
}
</script>

<template>
  <div class="grid gap-1">
    <ExamWorkspaceBodyParagraph
      v-for="(paragraph, paragraphIndex) in body"
      :key="paragraphIndex"
      :paragraph="paragraph"
      :paragraph-index="paragraphIndex"
      :owner="owner"
      :gaps="[]"
      :disabled="disabled"
      :border-class="borderClass"
      :interactive-gaps="false"
      :label="body.length > 1 ? `${label}, stycke ${paragraphIndex + 1}` : label"
      :test-id="body.length > 1 ? `${testId}-${paragraphIndex}` : testId"
      :aria-invalid="invalid ? 'true' : undefined"
      :aria-describedby="describedBy"
      :variant="variant"
      :asset-urls="assetUrls"
      @update-segments="(segments) => handleSegments(paragraphIndex, segments)"
      @toggle-heading="(level) => handleHeading(paragraphIndex, level)"
      @focus-paragraph="emit('focusEntry')"
    />
  </div>
</template>
