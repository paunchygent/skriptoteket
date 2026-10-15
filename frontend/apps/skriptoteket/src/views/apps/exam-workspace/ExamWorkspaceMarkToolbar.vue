<script setup lang="ts">
/**
 * Exam workspace formatting toolbar.
 *
 * Domain purpose:
 *   The compact glyph toolbar for the five kept marks and the three heading
 *   levels. Lucide glyphs follow the app's established icon imports (the
 *   shared catalogue is not adopted here). Every button keeps its exact
 *   size in every state. A pressed glyph shows
 *   what the selection already carries, the native tooltip and accessible
 *   name carry the action name, and a heading glyph toggles its level off
 *   when pressed again. Buttons keep the caret in the paragraph: mousedown is
 *   prevented so the selection never moves to the button.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceBodyEditor` above the question paragraphs.
 *   - Reads the glyph labels from `examWorkspaceBodyMarks`.
 */

import {
  Bold, Heading1, Heading2, Heading3, Italic, Subscript, Superscript, Underline,
} from "lucide-vue-next";

import { BODY_MARKS, MARK_LABELS } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";

type HeadingLevel = 1 | 2 | 3;

withDefaults(
  defineProps<{
    activeMarks?: BodyMark[];
    activeHeading?: HeadingLevel | null;
    disabled?: boolean;
    showHeadings?: boolean;
  }>(),
  { activeMarks: () => [], activeHeading: null, disabled: false, showHeadings: false },
);

const emit = defineEmits<{
  toggleMark: [mark: BodyMark];
  toggleHeading: [level: HeadingLevel];
}>();

const MARK_ICONS = {
  bold: Bold,
  italic: Italic,
  underline: Underline,
  superscript: Superscript,
  subscript: Subscript,
} as const;
const HEADING_ICONS = { 1: Heading1, 2: Heading2, 3: Heading3 } as const;

const HEADING_LEVELS: HeadingLevel[] = [1, 2, 3];

/** Control+B on Windows/Linux, Command+B on macOS, for the browser's own shortcut list. */
const MARK_SHORTCUTS: Partial<Record<BodyMark, string>> = {
  bold: "Control+B Meta+B",
  italic: "Control+I Meta+I",
  underline: "Control+U Meta+U",
};
</script>

<template>
  <div
    role="toolbar"
    aria-label="Formatering"
    class="flex items-center gap-0.5"
    @mousedown.prevent
  >
    <button
      v-for="mark in BODY_MARKS"
      :key="mark"
      type="button"
      class="inline-flex h-8 w-8 items-center justify-center border text-navy disabled:opacity-40"
      :class="
        activeMarks.includes(mark)
          ? 'border-navy/60 bg-panel-muted'
          : 'border-transparent hover:bg-canvas'
      "
      :aria-pressed="activeMarks.includes(mark) ? 'true' : 'false'"
      :aria-keyshortcuts="MARK_SHORTCUTS[mark]"
      :aria-label="MARK_LABELS[mark]"
      :title="MARK_LABELS[mark]"
      :disabled="disabled"
      :data-test="`exam-workspace-body-mark-${mark}`"
      @click="emit('toggleMark', mark)"
    >
      <component
        :is="MARK_ICONS[mark]"
        :size="16"
        aria-hidden="true"
      />
    </button>
    <template v-if="showHeadings">
      <span
        class="mx-1 h-5 w-px bg-navy/20"
        aria-hidden="true"
      />
      <button
        v-for="level in HEADING_LEVELS"
        :key="level"
        type="button"
        class="inline-flex h-8 w-8 items-center justify-center border text-navy disabled:opacity-40"
        :class="
          activeHeading === level
            ? 'border-navy/60 bg-panel-muted'
            : 'border-transparent hover:bg-canvas'
        "
        :aria-pressed="activeHeading === level ? 'true' : 'false'"
        :aria-label="`Rubrik ${level}`"
        :title="`Rubrik ${level}`"
        :disabled="disabled"
        :data-test="`exam-workspace-body-heading-${level}`"
        @click="emit('toggleHeading', level)"
      >
        <component
          :is="HEADING_ICONS[level]"
          :size="16"
          aria-hidden="true"
        />
      </button>
    </template>
  </div>
</template>
