/**
 * Exam workspace editor shortcut labels.
 *
 * Domain purpose:
 *   The per-platform text for every editor shortcut the toolbar names: the
 *   five marks, the three heading levels and the gap tool. Tooltips show the
 *   human label, `aria-keyshortcuts` carries the platform value.
 *
 * Relationships:
 *   - `ExamWorkspaceMarkToolbar` reads its button titles and
 *     `aria-keyshortcuts` values from here.
 */

import type { BodyMark } from "./examWorkspaceBodyMarks";

/** A mark the toolbar names a shortcut for. */
export type MarkShortcut = BodyMark;

/** Every action the toolbar names a shortcut for. */
export type EditorShortcut = MarkShortcut | "heading1" | "heading2" | "heading3" | "gapTool";

interface PlatformText {
  mac: string;
  other: string;
}

/** The human label per shortcut: Apple glyphs on macOS, Ctrl names elsewhere. */
const SHORTCUT_LABELS: Record<EditorShortcut, PlatformText> = {
  bold: { mac: "⌘B", other: "Ctrl+B" },
  italic: { mac: "⌘I", other: "Ctrl+I" },
  underline: { mac: "⌘U", other: "Ctrl+U" },
  superscript: { mac: "⌘.", other: "Ctrl+." },
  subscript: { mac: "⌘,", other: "Ctrl+," },
  heading1: { mac: "⌥⌘1", other: "Ctrl+Alt+1" },
  heading2: { mac: "⌥⌘2", other: "Ctrl+Alt+2" },
  heading3: { mac: "⌥⌘3", other: "Ctrl+Alt+3" },
  gapTool: { mac: "⌥⌘G", other: "Ctrl+Alt+G" },
};

/** The `aria-keyshortcuts` value per shortcut: Meta names on macOS, Control names elsewhere. */
const SHORTCUT_ARIA: Record<EditorShortcut, PlatformText> = {
  bold: { mac: "Meta+B", other: "Control+B" },
  italic: { mac: "Meta+I", other: "Control+I" },
  underline: { mac: "Meta+U", other: "Control+U" },
  superscript: { mac: "Meta+.", other: "Control+." },
  subscript: { mac: "Meta+,", other: "Control+," },
  heading1: { mac: "Meta+Alt+1", other: "Control+Alt+1" },
  heading2: { mac: "Meta+Alt+2", other: "Control+Alt+2" },
  heading3: { mac: "Meta+Alt+3", other: "Control+Alt+3" },
  gapTool: { mac: "Meta+Alt+G", other: "Control+Alt+G" },
};

/** Whether the viewer runs on macOS or iOS, like prosemirror-keymap decides it. */
export function isMacPlatform(): boolean {
  if (typeof navigator === "undefined") {
    return false;
  }
  return /Mac|iP(hone|[oa]d)/.test(navigator.platform);
}

/** The human label for a shortcut on the viewer's platform. */
export function shortcutLabel(shortcut: EditorShortcut, mac: boolean): string {
  return mac ? SHORTCUT_LABELS[shortcut].mac : SHORTCUT_LABELS[shortcut].other;
}

/** The `aria-keyshortcuts` value for a shortcut on the viewer's platform. */
export function ariaKeyshortcuts(shortcut: EditorShortcut, mac: boolean): string {
  return mac ? SHORTCUT_ARIA[shortcut].mac : SHORTCUT_ARIA[shortcut].other;
}
