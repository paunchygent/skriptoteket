/**
 * Exam workspace rich-text editor: the Tom lucka command and the empty gap's definition.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviour 9 and 10, Q9, L3):
 *   `insertEmptyGapAtCursor(gapId)` inserts an empty gap at the caret, or at
 *   a selection's end without deleting text, as one change that emits a single
 *   `createGap(body, gapId, "")` event and never `update`. It works with the
 *   gap tool on or off. The caret ends collapsed directly after the new chip.
 *   `gapDisabledReason` names why the command is unavailable: no next gap
 *   id. An empty gap is a Lucktext gap with no
 *   accepted answer in a question that has an answer key, or a dropdown gap
 *   with no correct option (`emptyGapIds`, reusing `gapHasAnswer`); a question
 *   without an answer key has none. `bodyWithoutEmptyGaps` removes every
 *   empty gap's placement, or returns null when there is nothing to remove.
 *
 * jsdom has no layout, so selections are set through TipTap commands and the
 * command is reached through the component's exposed `insertEmptyGap`, which
 * forwards the `nextGapId` prop to the composable.
 */

import { Editor } from "@tiptap/core";
import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { plainBody } from "./examWorkspaceRichText";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import {
  gap,
  paragraph,
  posIn,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  bodyWithoutEmptyGaps,
  emptyGapIds,
  gapDisabledReason,
} from "./useExamWorkspaceMakeGap";

type Body = NativeExamBodyParagraph[];
type Creation = [Body, string, string];

type OpenedEmptyGapEditor = {
  wrapper: VueWrapper;
  editor: Editor;
  creations: Creation[];
  updates: Array<[Body, boolean]>;
  insert: () => void;
};

const opened: VueWrapper[] = [];

async function openEmptyGapEditor(options: {
  body: Body;
  gapsInteractive?: boolean;
  disabled?: boolean;
  nextGapId?: string | null;
  gapTool?: boolean;
}): Promise<OpenedEmptyGapEditor> {
  const creations: Creation[] = [];
  const updates: Array<[Body, boolean]> = [];
  const keys = { undo: vi.fn(), redo: vi.fn(), canUndo: ref(false), canRedo: ref(false) };
  const editorRef = ref<InstanceType<typeof ExamWorkspaceRichTextEditor> | null>(null);
  const Host = defineComponent({
    setup() {
      provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys(keys);
      return () =>
        h(ExamWorkspaceRichTextEditor, {
          ref: editorRef,
          label: "Frågetext",
          testId: "editor-under-test",
          body: options.body,
          gapsInteractive: options.gapsInteractive,
          disabled: options.disabled,
          nextGapId: options.nextGapId,
          gapTool: options.gapTool,
          onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
          onCreateGap: (body: Body, gapId: string, seed: string) =>
            creations.push([body, gapId, seed]),
        });
    },
  });
  const wrapper = mount(Host, { attachTo: document.body });
  await nextTick();
  await nextTick();
  const surface = wrapper.get("[data-test='editor-under-test']").element;
  if (!(surface instanceof HTMLElement) || !("editor" in surface)) {
    throw new Error("the editor did not mount");
  }
  const attached = surface.editor;
  if (!(attached instanceof Editor)) {
    throw new Error("the editor did not mount");
  }
  opened.push(wrapper);
  return {
    wrapper,
    editor: attached,
    creations,
    updates,
    insert: () => editorRef.value?.insertEmptyGap(),
  };
}

afterEach(() => {
  while (opened.length > 0) {
    opened.pop()?.unmount();
  }
  document.body.innerHTML = "";
});

describe("ExamWorkspaceRichTextEditor Tom lucka", () => {
  it("inserts an empty gap at the caret as one createGap with an empty seed", async () => {
    const openedEditor = await openEmptyGapEditor({
      body: [paragraph(text("Solen lyser"))],
      gapsInteractive: true,
      nextGapId: "gap_001",
    });
    openedEditor.editor.commands.setTextSelection(posIn(openedEditor.editor, "lyser", 1));
    openedEditor.insert();

    expect(openedEditor.creations).toHaveLength(1);
    expect(openedEditor.updates).toHaveLength(0);
    const [body, gapId, seed] = openedEditor.creations[0]!;
    expect(gapId).toBe("gap_001");
    expect(seed).toBe("");
    expect(body).toEqual([paragraph(text("Solen l"), gap("gap_001"), text("yser"))]);
    // The caret ends collapsed directly after the new chip.
    expect(openedEditor.editor.state.selection.empty).toBe(true);
    let found = -1;
    openedEditor.editor.state.doc.descendants((node, pos) => {
      if (found < 0 && node.type.name === "examGap") {
        found = pos;
      }
      return found < 0;
    });
    expect(openedEditor.editor.state.selection.from).toBe(found + 1);
  });

  it("inserts at a selection's end and deletes no text", async () => {
    const openedEditor = await openEmptyGapEditor({
      body: [paragraph(text("ab cd"))],
      gapsInteractive: true,
      nextGapId: "gap_001",
    });
    openedEditor.editor.commands.setTextSelection({
      from: posIn(openedEditor.editor, "ab cd", 0),
      to: posIn(openedEditor.editor, "ab cd", 2),
    });
    openedEditor.insert();

    expect(openedEditor.creations).toHaveLength(1);
    const [body, gapId, seed] = openedEditor.creations[0]!;
    expect(gapId).toBe("gap_001");
    expect(seed).toBe("");
    expect(body).toEqual([paragraph(text("ab"), gap("gap_001"), text(" cd"))]);
    expect(openedEditor.editor.getText()).toBe("ab cd");
  });

  it("inserts with the gap tool on and with it off", async () => {
    const off = await openEmptyGapEditor({
      body: [paragraph(text("Solen lyser"))],
      gapsInteractive: true,
      nextGapId: "gap_001",
    });
    off.editor.commands.setTextSelection(posIn(off.editor, "lyser", 1));
    off.insert();
    expect(off.creations).toHaveLength(1);

    const on = await openEmptyGapEditor({
      body: [paragraph(text("Solen lyser"))],
      gapsInteractive: true,
      nextGapId: "gap_001",
      gapTool: true,
    });
    on.editor.commands.setTextSelection(posIn(on.editor, "lyser", 1));
    on.insert();
    expect(on.creations).toHaveLength(1);
    expect(on.creations[0]?.[2]).toBe("");
  });

  it("creates nothing for a selection spanning two paragraphs", async () => {
    const openedEditor = await openEmptyGapEditor({
      body: [paragraph(text("first")), paragraph(text("second"))],
      gapsInteractive: true,
      nextGapId: "gap_001",
    });
    openedEditor.editor.commands.setTextSelection({
      from: posIn(openedEditor.editor, "first", 2),
      to: posIn(openedEditor.editor, "second", 3),
    });
    openedEditor.insert();

    expect(openedEditor.creations).toHaveLength(0);
    expect(openedEditor.updates).toHaveLength(0);
  });

  it("creates nothing while not interactive, while disabled, or without a next gap id", async () => {
    const plain = await openEmptyGapEditor({
      body: [paragraph(text("Solen lyser"))],
      nextGapId: "gap_001",
    });
    plain.editor.commands.setTextSelection(posIn(plain.editor, "lyser", 1));
    plain.insert();
    expect(plain.creations).toHaveLength(0);

    const disabled = await openEmptyGapEditor({
      body: [paragraph(text("Solen lyser"))],
      gapsInteractive: true,
      disabled: true,
      nextGapId: "gap_001",
    });
    disabled.editor.commands.setTextSelection(posIn(disabled.editor, "lyser", 1));
    disabled.insert();
    expect(disabled.creations).toHaveLength(0);

    const capped = await openEmptyGapEditor({
      body: [paragraph(text("Solen lyser"))],
      gapsInteractive: true,
    });
    capped.editor.commands.setTextSelection(posIn(capped.editor, "lyser", 1));
    capped.insert();
    expect(capped.creations).toHaveLength(0);
  });
});

describe("gapDisabledReason", () => {
  it("is null with a next gap id", () => {
    expect(gapDisabledReason("gap_002")).toBeNull();
    expect(gapDisabledReason("gap_001")).toBeNull();
  });

  it("names the reason at the gap cap", () => {
    expect(gapDisabledReason(null)).toBe("Tom lucka – inga fler luckor kan läggas till i frågan");
    expect(gapDisabledReason(undefined)).toBe("Tom lucka – inga fler luckor kan läggas till i frågan");
  });
});

describe("emptyGapIds", () => {
  it("names a Lucktext gap with no accepted answer in a keyed question", () => {
    expect(emptyGapIds(buildGapItem())).toEqual(["gap_002"]);
  });

  it("is empty when every gap has an answer", () => {
    const item: NativeExamItem = buildGapItem({
      gaps: [buildGap("gap_001", ["100"]), buildGap("gap_002", ["noll"])],
    });
    expect(emptyGapIds(item)).toEqual([]);
  });

  it("names a dropdown gap with no correct option and keeps a keyed one", () => {
    const options = [
      { body: plainBody("zebra"), choice_id: "choice_001" },
      { body: plainBody("apa"), choice_id: "choice_002" },
    ];
    const item: NativeExamItem = buildGapItem({
      kind: "inline_choice",
      gaps: [
        buildGap("gap_001", [], { correct_option_id: "choice_001", options }),
        buildGap("gap_002", [], { correct_option_id: null, options }),
      ],
    });
    expect(emptyGapIds(item)).toEqual(["gap_002"]);
  });

  it("is empty for a question without an answer key", () => {
    const absent: NativeExamItem = buildGapItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    });
    expect(emptyGapIds(absent)).toEqual([]);
    const notApplicable: NativeExamItem = buildGapItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    });
    expect(emptyGapIds(notApplicable)).toEqual([]);
  });

  it("is empty for a question that is not a gap question", () => {
    expect(emptyGapIds(buildGapItem({ kind: "free_text", gaps: [] }))).toEqual([]);
  });
});

describe("bodyWithoutEmptyGaps", () => {
  it("removes every empty gap's placement and keeps the answered ones", () => {
    const cleaned = bodyWithoutEmptyGaps(buildGapItem());
    expect(cleaned?.flatMap((paragraph) => paragraph.segments)).toEqual(
      buildGapItem().body.flatMap((paragraph) => paragraph.segments).filter(
        (segment) => !(segment.kind === "gap" && segment.gap_id === "gap_002"),
      ),
    );
  });

  it("returns null when there is nothing to remove", () => {
    const answered: NativeExamItem = buildGapItem({
      gaps: [buildGap("gap_001", ["100"]), buildGap("gap_002", ["noll"])],
    });
    expect(bodyWithoutEmptyGaps(answered)).toBeNull();
    const unkeyed: NativeExamItem = buildGapItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    });
    expect(bodyWithoutEmptyGaps(unkeyed)).toBeNull();
  });
});
