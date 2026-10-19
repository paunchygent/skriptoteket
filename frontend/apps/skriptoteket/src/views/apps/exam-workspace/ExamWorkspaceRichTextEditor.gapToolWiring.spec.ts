/**
 * Exam workspace rich-text editor: the gap tool shortcut and Escape wiring.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 G1 wiring):
 *   Ctrl+Alt+G emits `toggleGapTool` while gaps are interactive (never while
 *   gaps are not interactive or while disabled), and Escape in the surface
 *   emits `escape`. A repeated Escape emits nothing, while a fresh one emits
 *   once. No floating button exists any more: the switch is the only control.
 *
 * Shared mount helpers live in `ExamWorkspaceRichTextEditor.gapTool.specSupport`;
 * pointer and selection conversion live in `ExamWorkspaceRichTextEditor.gapTool.spec`.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { paragraph, text } from "./ExamWorkspaceRichTextEditor.specSupport";
import type { Opened } from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import { closeGapToolEditors, openEditor } from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";

describe("ExamWorkspaceRichTextEditor gap tool wiring", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    closeGapToolEditors();
  });

  /** Ctrl+Alt+G as ProseMirror's keymap reads it: the key code comes from `keyCode`, as browsers set it. */
  function dispatchGapShortcut(
    wired: Opened,
    key: string,
    modifiers: { altKey?: boolean; ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean } = {},
  ): KeyboardEvent {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...modifiers });
    Object.defineProperty(event, "keyCode", { value: 71 });
    Object.defineProperty(event, "which", { value: 71 });
    wired.surface.dispatchEvent(event);
    return event;
  }

  function pressEscape(wired: Opened, init: KeyboardEventInit = {}): void {
    wired.surface.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true, ...init }),
    );
  }

  it("emits toggleGapTool on Ctrl+Alt+G while gaps are interactive", async () => {
    const wired = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });

    const event = dispatchGapShortcut(wired, "g", { ctrlKey: true, altKey: true });

    expect(wired.toggles).toHaveLength(1);
    expect(wired.escapes).toHaveLength(0);
    expect(event.defaultPrevented).toBe(true);
    expect(wired.editor.getText()).toBe("hello world");
  });

  it("does not emit toggleGapTool while gaps are not interactive or while disabled", async () => {
    const wired = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: false,
      nextGapId: "gap_002",
    });

    dispatchGapShortcut(wired, "g", { ctrlKey: true, altKey: true });
    expect(wired.toggles).toHaveLength(0);

    await wired.setProps({ gapsInteractive: true, disabled: true });
    const event = dispatchGapShortcut(wired, "g", { ctrlKey: true, altKey: true });
    expect(wired.toggles).toHaveLength(0);
    expect(event.defaultPrevented).toBe(false);
  });

  it("emits escape on Escape in the surface", async () => {
    const wired = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });

    pressEscape(wired);
    await nextTick();
    expect(wired.escapes).toHaveLength(1);
    expect(wired.toggles).toHaveLength(0);
  });

  it("emits no escape on a repeated Escape keydown, while a fresh one emits one", async () => {
    const wired = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });

    pressEscape(wired, { repeat: true });
    await nextTick();
    expect(wired.escapes).toHaveLength(0);

    pressEscape(wired);
    await nextTick();
    expect(wired.escapes).toHaveLength(1);
  });
});
