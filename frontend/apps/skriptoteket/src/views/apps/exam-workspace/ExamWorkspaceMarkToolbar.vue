<script setup lang="ts">
/**
 * Exam workspace formatting toolbar.
 *
 * Domain purpose:
 *   The compact glyph toolbar in four groups: Ångra and Gör om, the five kept
 *   marks, the gap tool switch and the three heading levels. Glyphs come from
 *   the shared catalogue through `UiGlyph` meanings, and the faces from the
 *   `.xw-tool` classes in `examWorkspace.css`. Every button keeps its exact
 *   size in every state. A pressed glyph shows
 *   what the selection already carries, the native tooltip and accessible
 *   name carry the action name, and a heading glyph toggles its level off
 *   when pressed again. Every tooltip and `aria-keyshortcuts` names its
 *   shortcut for the viewer's platform. Buttons keep the caret in the
 *   paragraph: mousedown is prevented so the selection never moves to the
 *   button.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceBodyEditor` above the question paragraphs.
 *   - Injects the workspace's Ångra and Gör om from `examWorkspaceHistoryKeys`;
 *     without a provider the first group and its separator are omitted.
 *   - Reads the glyph labels from `examWorkspaceBodyMarks` and the shortcut
 *     text from `examWorkspaceShortcutLabels`.
 */

import { UiGlyph } from "../../../components/ui";
import { BODY_MARKS, MARK_LABELS } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { examWorkspaceShortcut } from "./examWorkspaceFormat";
import { useExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
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
}>();

const history = useExamWorkspaceHistoryKeys();

const HEADING_LEVELS: HeadingLevel[] = [1, 2, 3];
const HEADING_MEANINGS = { 1: "heading-1", 2: "heading-2", 3: "heading-3" } as const;

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
    class="xw-toolbar"
    @mousedown.prevent
  >
    <template v-if="history">
      <div class="xw-tools">
        <button
          type="button"
          class="xw-tool"
          :disabled="!history.canUndo.value"
          :title="history.canUndo.value ? `Ångra (${examWorkspaceShortcut('Z', false, isMac)})` : 'Inget att ångra'"
          aria-label="Ångra"
          aria-keyshortcuts="Control+Z Meta+Z"
          data-test="exam-workspace-undo"
          @click="history.undo()"
        >
          <UiGlyph
            meaning="undo"
            :size="16"
          />
        </button>
        <button
          type="button"
          class="xw-tool"
          :disabled="!history.canRedo.value"
          :title="history.canRedo.value ? `Gör om (${examWorkspaceShortcut('Z', true, isMac)})` : 'Inget att göra om'"
          aria-label="Gör om"
          aria-keyshortcuts="Control+Shift+Z Meta+Shift+Z"
          data-test="exam-workspace-redo"
          @click="history.redo()"
        >
          <UiGlyph
            meaning="redo"
            :size="16"
          />
        </button>
      </div>
      <span
        class="xw-toolsep"
        aria-hidden="true"
      />
    </template>
    <div class="xw-tools">
      <button
        v-for="mark in BODY_MARKS"
        :key="mark"
        type="button"
        class="xw-tool"
        :aria-pressed="activeMarks.includes(mark) ? 'true' : 'false'"
        :aria-keyshortcuts="ariaKeyshortcuts(mark, isMac)"
        :aria-label="MARK_LABELS[mark]"
        :title="`${MARK_LABELS[mark]} (${shortcutLabel(mark, isMac)})`"
        :disabled="disabled"
        :data-test="`exam-workspace-body-mark-${mark}`"
        @click="emit('toggleMark', mark)"
      >
        <UiGlyph
          :meaning="mark"
          :size="16"
        />
      </button>
    </div>
    <template v-if="showGap">
      <span
        class="xw-toolsep"
        aria-hidden="true"
      />
      <div class="xw-tools">
        <!-- Tom lucka (empty-gap insert) is pending TASK-SKRIPT-40-04-13's insert command. -->
        <button
          type="button"
          class="xw-tool xw-tool--switch"
          :aria-pressed="gapToolOn ? 'true' : 'false'"
          :aria-keyshortcuts="ariaKeyshortcuts('gapTool', isMac)"
          aria-label="Luckverktyg"
          :title="gapToolDisabledReason ?? `Luckverktyg (${shortcutLabel('gapTool', isMac)})`"
          :disabled="disabled || gapToolDisabledReason !== null"
          data-test="exam-workspace-toolbar-gap-tool"
          @click="emit('toggleGapTool')"
        >
          <UiGlyph
            meaning="gap-tool"
            :size="16"
          />
        </button>
      </div>
    </template>
    <template v-if="showHeadings">
      <span
        class="xw-toolsep"
        aria-hidden="true"
      />
      <div class="xw-tools">
        <button
          v-for="level in HEADING_LEVELS"
          :key="level"
          type="button"
          class="xw-tool"
          :aria-pressed="activeHeading === level ? 'true' : 'false'"
          :aria-keyshortcuts="ariaKeyshortcuts(HEADING_SHORTCUTS[level], isMac)"
          :aria-label="`Rubrik ${level}`"
          :title="`Rubrik ${level} (${shortcutLabel(HEADING_SHORTCUTS[level], isMac)})`"
          :disabled="disabled"
          :data-test="`exam-workspace-body-heading-${level}`"
          @click="emit('toggleHeading', level)"
        >
          <UiGlyph
            :meaning="HEADING_MEANINGS[level]"
            :size="16"
          />
        </button>
      </div>
    </template>
  </div>
</template>
