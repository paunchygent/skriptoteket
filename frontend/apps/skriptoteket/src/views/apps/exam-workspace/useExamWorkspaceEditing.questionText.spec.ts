/**
 * Exam workspace editing session: the question text as one document.
 *
 * Expected behavior (TASK-SKRIPT-40-04-06 D1, D2, D3):
 *   - A body edit replaces the item's whole body, drops the records of gaps
 *     it no longer places and the assets nothing references any more, in the
 *     same step; Ångra installs the stored step's document, so text, gap
 *     record and asset record return together.
 *   - A picture still referenced by another item, the exam instruction or a
 *     part instruction keeps its asset record.
 *   - Deleting the last gap of a gap_fill question saves with no gap.
 *   - The saved document carries the edit's outcome: the same body, gap
 *     records and asset records as the copy. Whether a native document is
 *     valid stays with the backend tests.
 *
 * The edit is made through the real question-text editor mounted on the
 * production editing session; transport is the named double of the server's
 * step store.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick } from "vue";

import type { NativeExamDocument, NativeExamItem, NativeExamParent } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { buildGapItem, posIn, press, surface, tiptap } from "./ExamWorkspaceBodyEditor.specSupport";
import type { MountedBodyEditor } from "./ExamWorkspaceBodyEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { exam, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  unmountEditors();
  stopScopes();
  document.body.innerHTML = "";
});

/** Canonical asset ids: the server accepts `asset_` and sixteen hex digits. */
const PICTURE = "asset_0000000000000001";
const OTHER_PICTURE = "asset_0000000000000002";

function asset(assetId: string): NativeExamDocument["assets"][number] {
  return { asset_id: assetId, byte_length: 10, media_type: "image/png", sha256: "0".repeat(64) };
}

function pictureOnly(assetId: string): NativeExamItem["body"] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

const GAP_RECORDS = [buildGap("gap_001", ["100"]), buildGap("gap_002", ["0"])];

/** "A [gap_001] B [gap_002] C" and "[PICTURE] D": a gap ends paragraph one's run, a picture opens paragraph two. */
function mergeItem(): NativeExamItem {
  return buildGapItem({
    body: [
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "A " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: " B " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", marks: [], text: " C" },
        ],
      },
      {
        heading_level: null,
        segments: [{ asset_id: PICTURE, kind: "asset" }, { kind: "text", marks: [], text: " D" }],
      },
    ],
    gaps: GAP_RECORDS,
  });
}

/** Item 1 is the merge item (gaps 1-2, PICTURE); item 2 starts as a free-text question. */
function baseline(overrides: Partial<NativeExamDocument> = {}, secondBody?: NativeExamItem["body"]): NativeExamDocument {
  const document = exam("Prov", 2);
  const second = secondBody === undefined ? document.items[1]! : { ...document.items[1]!, body: secondBody };
  return { ...document, assets: [asset(PICTURE)], items: [mergeItem(), second], ...overrides };
}

/** The merge item's document where item 2 holds its own picture, whose record the edit must keep. */
function baselineWithOtherPicture(): NativeExamDocument {
  return baseline({ assets: [asset(PICTURE), asset(OTHER_PICTURE)] }, pictureOnly(OTHER_PICTURE));
}

/** The merge item's document where PICTURE is also placed by item 2, the exam instruction or a part instruction. */
function baselineSharingPicture(shared: "item" | "instructions" | "parent"): NativeExamDocument {
  const parent: NativeExamParent = {
    parent_id: "parent_001",
    instruction: pictureOnly(PICTURE),
    item_ids: ["item_002"],
    place: 1,
  };
  const overrides: Partial<NativeExamDocument> = { assets: [asset(PICTURE)] };
  if (shared === "instructions") overrides.instructions = pictureOnly(PICTURE);
  if (shared === "parent") overrides.parents = [parent];
  return baseline(overrides, shared === "item" ? pictureOnly(PICTURE) : undefined);
}

/** "Svar: [gap_001]" with its one gap, no picture. */
function onlyGapItem(item: NativeExamItem): NativeExamItem {
  return {
    ...item,
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Svar: " }, { kind: "gap", gap_id: "gap_001" }] }],
    gaps: [buildGap("gap_001", ["100"])],
  };
}

function sentDocument(): NativeExamDocument {
  return api.saveExamWorkspaceDocument.mock.calls[0]![1].document;
}

const mounted: VueWrapper[] = [];

function unmountEditors(): void {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
}

/**
 * The question-text editor on the editing session's first item, wired as the
 * workspace wires it: edits go to `updateItemBody`, Ctrl/Cmd+Z to Ångra.
 */
async function mountQuestionText(editing: Awaited<ReturnType<typeof openEditing>>["editing"]): Promise<MountedBodyEditor> {
  const Host = defineComponent({
    setup() {
      provideExamWorkspaceHistoryKeys({
        undo: () => void editing.history.undo(),
        redo: () => void editing.history.redo(),
      });
      const item = computed(() => editing.workspaceDocument.value!.items[0]!);
      return () =>
        h(ExamWorkspaceBodyEditor, {
          item: item.value,
          onUpdateBody: editing.updateItemBody,
          onShowGapAsText: editing.showItemGapAsText,
        });
    },
  });
  const host = mount(Host, { attachTo: document.body });
  mounted.push(host);
  await nextTick();
  await nextTick();
  return host.findComponent(ExamWorkspaceBodyEditor);
}

function pictureEnd(wrapper: MountedBodyEditor, assetId: string): number {
  let end = -1;
  tiptap(wrapper).state.doc.descendants((node, pos) => {
    if (node.type.name === "examPicture" && node.attrs.assetId === assetId) end = pos + node.nodeSize;
    return end < 0;
  });
  return end;
}

/** Select from inside " B " in paragraph one to just after the picture in paragraph two. */
function selectAcrossGapAndPicture(wrapper: MountedBodyEditor): void {
  const editor = tiptap(wrapper);
  editor.commands.setTextSelection({ from: posIn(editor, " B ", 2), to: pictureEnd(wrapper, PICTURE) });
}

const AFTER_CROSS_PARAGRAPH_DELETE: NativeExamItem["body"] = [
  {
    heading_level: null,
    segments: [
      { kind: "text", marks: [], text: "A " },
      { kind: "gap", gap_id: "gap_001" },
      { kind: "text", marks: [], text: " B D" },
    ],
  },
];

describe("question text edits keep gap and picture records consistent", () => {
  it("drops the gap record and the unreferenced asset with a cross-paragraph delete, and Ångra restores both", async () => {
    const original = baselineWithOtherPicture();
    const { editing } = await openEditing(api, original);
    const wrapper = await mountQuestionText(editing);
    selectAcrossGapAndPicture(wrapper);

    press(surface(wrapper), "Backspace");
    await nextTick();

    const edited = editing.workspaceDocument.value!;
    expect(edited.items[0]!.body).toEqual(AFTER_CROSS_PARAGRAPH_DELETE);
    // Exactly the removed gap's record and the removed picture's record go; the other picture's stays.
    expect(edited.items[0]!.gaps).toEqual([buildGap("gap_001", ["100"])]);
    expect(edited.assets).toEqual([asset(OTHER_PICTURE)]);
    expect(surface(wrapper).querySelector("[data-asset-id]")).toBeNull();

    // The save payload carries the same outcome.
    expect(await editing.save()).toBe(true);
    expect(sentDocument().items[0]!.body).toEqual(AFTER_CROSS_PARAGRAPH_DELETE);
    expect(sentDocument().items[0]!.gaps).toEqual([buildGap("gap_001", ["100"])]);
    expect(sentDocument().assets).toEqual([asset(OTHER_PICTURE)]);

    await editing.history.undo();
    await flushPromises();
    const restored = editing.workspaceDocument.value!;
    expect(restored.items[0]!.body).toEqual(original.items[0]!.body);
    expect(restored.items[0]!.gaps).toEqual(GAP_RECORDS);
    expect(restored.assets).toEqual([asset(PICTURE), asset(OTHER_PICTURE)]);
    expect(restored.items[0]).toEqual(original.items[0]);
    // The editor shows the restored text, gap and picture.
    expect(surface(wrapper).querySelector('[data-gap-id="gap_002"]')).not.toBeNull();
    expect(surface(wrapper).querySelector(`[data-asset-id="${PICTURE}"]`)).not.toBeNull();
    unmountEditors();
  });

  it("Ctrl+Z in the question text runs the workspace Ångra and restores the records", async () => {
    const original = baselineWithOtherPicture();
    const { editing } = await openEditing(api, original);
    const wrapper = await mountQuestionText(editing);
    selectAcrossGapAndPicture(wrapper);
    press(surface(wrapper), "Backspace");
    await nextTick();
    expect(editing.workspaceDocument.value!.assets).toEqual([asset(OTHER_PICTURE)]);
    expect(editing.workspaceDocument.value!.items[0]!.gaps).toEqual([buildGap("gap_001", ["100"])]);

    const event = press(surface(wrapper), "z", { ctrlKey: true });
    await vi.waitFor(() =>
      expect(editing.workspaceDocument.value!.assets).toEqual([asset(PICTURE), asset(OTHER_PICTURE)]),
    );

    expect(event.defaultPrevented).toBe(true);
    expect(editing.workspaceDocument.value!.items[0]!.gaps).toEqual(GAP_RECORDS);
    expect(editing.workspaceDocument.value!.items[0]).toEqual(original.items[0]);
    unmountEditors();
  });

  it("keeps an asset another item, the exam instruction or a part instruction still references", async () => {
    for (const shared of ["item", "instructions", "parent"] as const) {
      stopScopes();
      const { editing } = await openEditing(api, baselineSharingPicture(shared));
      const wrapper = await mountQuestionText(editing);
      selectAcrossGapAndPicture(wrapper);

      press(surface(wrapper), "Backspace");
      await nextTick();

      const edited = editing.workspaceDocument.value!;
      expect(edited.items[0]!.body).toEqual(AFTER_CROSS_PARAGRAPH_DELETE);
      expect(edited.items[0]!.gaps).toEqual([buildGap("gap_001", ["100"])]);
      expect(edited.assets).toEqual([asset(PICTURE)]);
      unmountEditors();
    }
  });

  it("saves a gap_fill question with no gap after its last gap is deleted", async () => {
    const start = baseline({ assets: [] });
    start.items[0] = onlyGapItem(start.items[0]!);
    const { editing } = await openEditing(api, start);
    const wrapper = await mountQuestionText(editing);
    const editor = tiptap(wrapper);
    let gapPos = -1;
    editor.state.doc.descendants((node, pos) => {
      if (node.type.name === "examGap") gapPos = pos;
      return gapPos < 0;
    });
    editor.commands.setNodeSelection(gapPos);

    press(surface(wrapper), "Backspace");
    await nextTick();

    const edited = editing.workspaceDocument.value!.items[0]!;
    expect(edited.gaps).toEqual([]);
    expect(edited.body[0]!.segments).toEqual([{ kind: "text", marks: [], text: "Svar: " }]);
    expect(await editing.save()).toBe(true);
    expect(sentDocument().items[0]!.gaps).toEqual([]);
    expect(sentDocument().items[0]!.body[0]!.segments).toEqual([{ kind: "text", marks: [], text: "Svar: " }]);
    expect(sentDocument().assets).toEqual([]);
    unmountEditors();
  });

  it("saves the empty body when the whole text, only gap included, is deleted", async () => {
    const start = baseline({ assets: [] });
    start.items[0] = onlyGapItem(start.items[0]!);
    const { editing } = await openEditing(api, start);
    const wrapper = await mountQuestionText(editing);
    tiptap(wrapper).commands.selectAll();

    press(surface(wrapper), "Backspace");
    await nextTick();

    const edited = editing.workspaceDocument.value!.items[0]!;
    expect(edited.body).toEqual([]);
    expect(edited.gaps).toEqual([]);
    expect(await editing.save()).toBe(true);
    expect(sentDocument().items[0]!.body).toEqual([]);
    expect(sentDocument().items[0]!.gaps).toEqual([]);
    unmountEditors();
  });

  it("shows the only gap as text, leaving a question with no gap", async () => {
    const start = baseline({ assets: [] });
    start.items[0] = onlyGapItem(start.items[0]!);
    const { editing } = await openEditing(api, start);

    editing.showItemGapAsText("item_001", "gap_001");

    const item = editing.workspaceDocument.value!.items[0]!;
    expect(item.gaps).toEqual([]);
    expect(item.body[0]!.segments.map((segment) => (segment.kind === "text" ? segment.text : segment.kind))).toEqual([
      "Svar: ",
      "100",
    ]);
    expect(editing.workspaceDocument.value!.assets).toEqual([]);
  });

  it("starts a new question's blank choices with an empty body", async () => {
    const { newTeacherItem } = await import("./examWorkspaceItemEdits");

    const single = newTeacherItem("item_009", 9, "single_choice");
    const matching = newTeacherItem("item_010", 10, "matching");

    expect(single.choices.map((choice) => choice.body)).toEqual([[], []]);
    expect(matching.match_left.map((entry) => entry.body)).toEqual([[]]);
    expect(matching.match_right.map((entry) => entry.body)).toEqual([[], []]);
  });
});
