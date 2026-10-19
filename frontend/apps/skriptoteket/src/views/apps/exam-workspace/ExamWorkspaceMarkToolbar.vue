<script setup lang="ts">
/**
 * Exam workspace formatting toolbar.
 *
 * Domain purpose:
 *   The compact glyph toolbar for the five kept marks, the three heading
 *   levels and the gap tool. Lucide glyphs follow the app's established icon
 *   imports (the shared catalogue is not adopted here). Every button keeps its
 *   exact size in every state. It declares the Tom lucka `insertEmptyGap`
 *   emit; no button is wired to it yet
 *   (TASK-SKRIPT-40-04-17 wires a glyph later). A pressed glyph shows
 *   what the selection already carries, the native tooltip and accessible
 *   name carry the action name, and a heading glyph toggles its level off
 *   when pressed again. Every tooltip and `aria-keyshortcuts` names its
 *   shortcut for the viewer's platform. Buttons keep the caret in the
 *   paragraph: mousedown is prevented so the selection never moves to the
 *   button.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceBodyEditor` above the question paragraphs.
 *   - Reads the glyph labels from `examWorkspaceBodyMarks` and the shortcut
 *     text from `examWorkspaceShortcutLabels`.
 */

import {
  Bold, Heading1, Heading2, Heading3, Italic, MousePointerClick, Subscript, Superscript, Underline,
} from "lucide-vue-next";

import { BODY_MARKS, MARK_LABELS } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { ariaKeyshortcuts, isMacPlatform, shortcutLabel } from "./examWorkspaceShortcutLabels";
import type { EditorShortcut } from "./examWorkspaceShortcutLabels";

type HeadingLevel = 1 | 2 | 3;

withDefaults(
  defineProps<{
    activeMarks?: BodyMark[];
    activeHeading?: HeadingLevel | null;
    disabled?: boolean;
    showHeadings?: boolean;
    /** Show the gap tool toggle after the marks. */
    showGap?: boolean;
    /** Why the gap tool toggle is off at the cap; disables the toggle while set. */
    gapToolDisabledReason?: string | null;
    /** Whether the gap tool toggle reads pressed. */
    gapToolOn?: boolean;
  }>(),
  { activeMarks: () => [], activeHeading: null, disabled: false, showHeadings: false, showGap: false, gapToolDisabledReason: null, gapToolOn: false },
);

const emit = defineEmits<{
  toggleMark: [mark: BodyMark];
  toggleHeading: [level: HeadingLevel];
  toggleGapTool: [];
  /** Tom lucka: the body editor inserts one empty gap at the caret. No button yet: TASK-SKRIPT-40-04-17 wires a glyph to this emit later. */
  insertEmptyGap: [];
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

const HEADING_SHORTCUTS: Record<HeadingLevel, EditorShortcut> = {
  1: "heading1",
  2: "heading2",
  3: "heading3",
};

/** The viewer's platform, read once: macOS glyphs or Ctrl names in every tooltip. */
const isMac = isMacPlatform();
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
      :aria-keyshortcuts="ariaKeyshortcuts(mark, isMac)"
      :aria-label="MARK_LABELS[mark]"
      :title="`${MARK_LABELS[mark]} (${shortcutLabel(mark, isMac)})`"
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
    <button
      v-if="showGap"
      type="button"
      class="inline-flex h-8 w-8 items-center justify-center border text-navy disabled:opacity-40"
      :class="
        gapToolOn
          ? 'border-navy/60 bg-panel-muted'
          : 'border-transparent hover:bg-canvas'
      "
      :aria-pressed="gapToolOn ? 'true' : 'false'"
      :aria-keyshortcuts="ariaKeyshortcuts('gapTool', isMac)"
      aria-label="Luckverktyg"
      :title="gapToolDisabledReason ?? `Luckverktyg (${shortcutLabel('gapTool', isMac)})`"
      :disabled="disabled || gapToolDisabledReason !== null"
      data-test="exam-workspace-toolbar-gap-tool"
      @click="emit('toggleGapTool')"
    >
      <MousePointerClick
        :size="16"
        aria-hidden="true"
      />
    </button>
    <template v-if="showHeadings">
      <span
        class="mx-1.5 h-5 w-px bg-navy/40"
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
        :aria-keyshortcuts="ariaKeyshortcuts(HEADING_SHORTCUTS[level], isMac)"
        :aria-label="`Rubrik ${level}`"
        :title="`Rubrik ${level} (${shortcutLabel(HEADING_SHORTCUTS[level], isMac)})`"
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
