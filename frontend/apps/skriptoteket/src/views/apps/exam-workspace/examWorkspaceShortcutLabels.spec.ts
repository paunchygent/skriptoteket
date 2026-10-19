/**
 * Exam workspace editor shortcut labels.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 G3):
 *   Every toolbar shortcut has a Mac and a non-Mac human label and an
 *   `aria-keyshortcuts` value. `isMacPlatform` matches Apple's platforms the
 *   way prosemirror-keymap does. Every stored mark has a shortcut entry for
 *   both platforms, so no mark button renders without its shortcut.
 */

import { afterEach, describe, expect, it } from "vitest";

import { BODY_MARKS } from "./examWorkspaceBodyMarks";
import {
  ariaKeyshortcuts,
  isMacPlatform,
  shortcutLabel,
} from "./examWorkspaceShortcutLabels";
import type { EditorShortcut } from "./examWorkspaceShortcutLabels";

const CASES: Array<{
  shortcut: EditorShortcut;
  mac: string;
  other: string;
  macAria: string;
  otherAria: string;
}> = [
  { shortcut: "bold", mac: "⌘B", other: "Ctrl+B", macAria: "Meta+B", otherAria: "Control+B" },
  { shortcut: "italic", mac: "⌘I", other: "Ctrl+I", macAria: "Meta+I", otherAria: "Control+I" },
  { shortcut: "underline", mac: "⌘U", other: "Ctrl+U", macAria: "Meta+U", otherAria: "Control+U" },
  { shortcut: "superscript", mac: "⌘.", other: "Ctrl+.", macAria: "Meta+.", otherAria: "Control+." },
  { shortcut: "subscript", mac: "⌘,", other: "Ctrl+,", macAria: "Meta+,", otherAria: "Control+," },
  { shortcut: "heading1", mac: "⌥⌘1", other: "Ctrl+Alt+1", macAria: "Meta+Alt+1", otherAria: "Control+Alt+1" },
  { shortcut: "heading2", mac: "⌥⌘2", other: "Ctrl+Alt+2", macAria: "Meta+Alt+2", otherAria: "Control+Alt+2" },
  { shortcut: "heading3", mac: "⌥⌘3", other: "Ctrl+Alt+3", macAria: "Meta+Alt+3", otherAria: "Control+Alt+3" },
  { shortcut: "gapTool", mac: "⌥⌘G", other: "Ctrl+Alt+G", macAria: "Meta+Alt+G", otherAria: "Control+Alt+G" },
];

const originalPlatform = navigator.platform;

function setPlatform(platform: string): void {
  Object.defineProperty(navigator, "platform", { value: platform, configurable: true });
}

afterEach(() => {
  Object.defineProperty(navigator, "platform", { value: originalPlatform, configurable: true });
});

describe("examWorkspaceShortcutLabels", () => {
  it("names every shortcut's Mac and non-Mac label and aria value", () => {
    for (const entry of CASES) {
      expect(shortcutLabel(entry.shortcut, true)).toBe(entry.mac);
      expect(shortcutLabel(entry.shortcut, false)).toBe(entry.other);
      expect(ariaKeyshortcuts(entry.shortcut, true)).toBe(entry.macAria);
      expect(ariaKeyshortcuts(entry.shortcut, false)).toBe(entry.otherAria);
    }
  });

  it("gives every stored mark a label and aria value on both platforms", () => {
    for (const mark of BODY_MARKS) {
      for (const mac of [true, false]) {
        expect(shortcutLabel(mark, mac).length).toBeGreaterThan(0);
        expect(ariaKeyshortcuts(mark, mac).length).toBeGreaterThan(0);
      }
      expect(shortcutLabel(mark, true)).not.toBe(shortcutLabel(mark, false));
    }
  });

  it("reads macOS platforms like prosemirror-keymap", () => {
    setPlatform("MacIntel");
    expect(isMacPlatform()).toBe(true);

    setPlatform("iPad");
    expect(isMacPlatform()).toBe(true);
  });

  it("reads Windows and Linux as non-Mac", () => {
    setPlatform("Win32");
    expect(isMacPlatform()).toBe(false);

    setPlatform("Linux x86_64");
    expect(isMacPlatform()).toBe(false);
  });
});
