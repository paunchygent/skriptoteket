/**
 * Exam workspace rich-text editor: the gap command.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviours 8 and 9):
 *   `target.makeGap(gapId)` turns the selection, or the word at the caret,
 *   into a new gap, as one change that emits a single
 *   `createGap(body, gapId, seed)` event and never `update`. A caret outside
 *   a word creates nothing: no control inserts an empty gap.
 *
 * jsdom has no layout, so selections are set through TipTap commands.
 */

import { TextSelection } from "@tiptap/pm/state";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  atomPos,
  gap,
  paragraph,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  openEditor,
  releaseOpenedEditors,
  targetOf,
} from "./ExamWorkspaceRichTextEditor.makeGap.specSupport";

describe("ExamWorkspaceRichTextEditor makeGap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    releaseOpenedEditors();
    releaseEditor();
  });

  it("turns the word at the caret into a gap in exactly one createGap event", async () => {
    const opened = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))], gapsInteractive: true });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("Paris");
    expect(body).toEqual([paragraph(text("Huvudstaden är "), gap("gap_002"), text("."))]);
    expect(opened.editor.state.selection).toBeInstanceOf(TextSelection);
    expect(opened.editor.state.selection.empty).toBe(true);
    expect(opened.editor.state.selection.from).toBe(atomPos(opened.editor, "examGap") + 1);
  });

  it("turns the word at a caret inside a bold mark into the whole word across the mark", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Stock"), text("holm", ["bold"]), text("."))],
      gapsInteractive: true,
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "holm", 2));
    const target = targetOf(opened);
    const dispatch = vi.spyOn(opened.editor.view, "dispatch");
    target.makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("Stockholm");
    expect(body).toEqual([paragraph(text("Huvudstaden är "), gap("gap_002"), text("."))]);
    expect(opened.editor.state.selection).toBeInstanceOf(TextSelection);
    expect(opened.editor.state.selection.empty).toBe(true);
    expect(opened.editor.state.selection.from).toBe(atomPos(opened.editor, "examGap") + 1);
    expect(dispatch).toHaveBeenCalledTimes(1);
  });

  it("turns a selected range into one gap seeded with the trimmed text", async () => {
    const opened = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))], gapsInteractive: true });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "är Paris", 0),
      to: posIn(opened.editor, "är Paris", 8),
    });
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("är Paris");
    expect(body).toEqual([paragraph(text("Huvudstaden "), gap("gap_002"), text("."))]);
  });

  it("turns only the word after an existing gap into a gap", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Solen är "), gap("gap_001"), text("varm idag"))],
      gapsInteractive: true,
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "varm", 1));
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("varm");
    expect(body).toEqual([
      paragraph(text("Solen är "), gap("gap_001"), gap("gap_002"), text(" idag")),
    ]);
  });

  it("does nothing for a selection spanning a gap atom", async () => {
    const opened = await openEditor({
      body: [paragraph(text("a"), gap("gap_001"), text("b"))],
      gapsInteractive: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "a", 1),
      to: posIn(opened.editor, "b", 0),
    });
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("ab");
  });

  it("does nothing for a selection spanning two paragraphs", async () => {
    const opened = await openEditor({
      body: [paragraph(text("first")), paragraph(text("second"))],
      gapsInteractive: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "first", 2),
      to: posIn(opened.editor, "second", 3),
    });
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("first\n\nsecond");
  });

  it("creates nothing at a caret outside a word, never an empty gap", async () => {
    const opened = await openEditor({ body: [paragraph(text("ab "))], gapsInteractive: true });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "ab ", 3));
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("ab ");
  });

  it("does nothing while not interactive or while disabled", async () => {
    const plain = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))] });
    plain.editor.commands.setTextSelection(posIn(plain.editor, "Paris", 1));
    plain.surface.focus();
    expect(plain.registry.active.value).not.toBeNull();
    plain.registry.active.value?.makeGap("gap_002");
    expect(plain.creations).toHaveLength(0);
    expect(plain.updates).toHaveLength(0);
    expect(plain.editor.getText()).toBe("Huvudstaden är Paris.");

    const disabled = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      disabled: true,
    });
    disabled.editor.commands.setTextSelection(posIn(disabled.editor, "Paris", 1));
    disabled.surface.focus();
    disabled.registry.active.value?.makeGap("gap_002");
    expect(disabled.creations).toHaveLength(0);
    expect(disabled.updates).toHaveLength(0);
    expect(disabled.editor.getText()).toBe("Huvudstaden är Paris.");
  });

  it("keeps the caret after the gap when the owner echoes the emitted body", async () => {
    const opened = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))], gapsInteractive: true });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    targetOf(opened).makeGap("gap_002");
    const [emitted] = opened.creations[0]!;

    await opened.setProps({ body: emitted });

    expect(opened.editor.state.selection).toBeInstanceOf(TextSelection);
    expect(opened.editor.state.selection.empty).toBe(true);
    expect(opened.editor.state.selection.from).toBe(atomPos(opened.editor, "examGap") + 1);
    expect(opened.editor.getText()).toBe("Huvudstaden är .");
    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
  });
});
