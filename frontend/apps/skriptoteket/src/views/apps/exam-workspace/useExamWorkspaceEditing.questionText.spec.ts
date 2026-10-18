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
 *   - Every document the save sends obeys the server's rules: each asset is
 *     referenced and declared, each gap is placed once and has its record.
 *
 * The edit is made through the real question-text editor mounted on the
 * production editing session; transport is the named double of the server's
 * step store.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick } from "vue";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { buildMergeItem, posIn, press, surface, tiptap } from "./ExamWorkspaceBodyEditor.specSupport";
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
  stopScopes();
  document.body.innerHTML = "";
});

function asset(assetId: string): NativeExamDocument["assets"][number] {
  return { asset_id: assetId, byte_length: 10, media_type: "image/png", sha256: "0".repeat(64) };
}

function pictureOnly(assetId: string): NativeExamItem["body"] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

/** Item 1 is the merge item (gaps 1-2, asset_001); item 2 starts as a free-text question. */
function baseline(overrides: Partial<NativeExamDocument> = {}, secondBody?: NativeExamItem["body"]): NativeExamDocument {
  const document = exam("Prov", 2);
  const first: NativeExamItem = {
    ...buildMergeItem(),
    gaps: [buildGap("gap_001", ["100"]), buildGap("gap_002", ["0"])],
  };
  const second = secondBody === undefined ? document.items[1]! : { ...document.items[1]!, body: secondBody };
  return { ...document, assets: [asset("asset_001")], items: [first, second], ...overrides };
}

/** "Svar: [gap_001]" with its one gap, no picture. */
function onlyGapItem(item: NativeExamItem): NativeExamItem {
  return {
    ...item,
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Svar: " }, { kind: "gap", gap_id: "gap_001" }] }],
    gaps: [buildGap("gap_001", ["100"])],
  };
}

/** The server's document rules for gaps and pictures (native_exam_document.py). */
function expectServerValid(document: NativeExamDocument): void {
  const declared = document.assets.map((entry) => entry.asset_id);
  expect(new Set(declared).size).toBe(declared.length);
  const referenced = new Set<string>();
  const bodies = [
    document.instructions,
    ...document.parents.map((parent) => parent.instruction),
    ...document.items.map((item) => item.body),
  ];
  for (const body of bodies) {
    for (const paragraph of body) {
      for (const segment of paragraph.segments) {
        if (segment.kind === "asset") referenced.add(segment.asset_id);
      }
    }
  }
  expect([...referenced].sort()).toEqual([...declared].sort());
  for (const item of document.items) {
    const placed = item.body.flatMap((paragraph) =>
      paragraph.segments.flatMap((segment) => (segment.kind === "gap" ? [segment.gap_id] : [])),
    );
    expect(new Set(placed).size).toBe(placed.length);
    expect(item.gaps.map((gap) => gap.gap_id).sort()).toEqual([...placed].sort());
  }
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
  const wrapper = mount(Host, { attachTo: document.body });
  await nextTick();
  await nextTick();
  return wrapper as unknown as MountedBodyEditor;
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
  editor.commands.setTextSelection({ from: posIn(editor, " B ", 2), to: pictureEnd(wrapper, "asset_001") });
}

describe("question text edits keep gap and picture records consistent", () => {
  it("drops the gap record and the unreferenced asset with a cross-paragraph delete, and Ångra restores both", async () => {
    const original = baseline();
    const { editing } = await openEditing(api, original);
    const wrapper = await mountQuestionText(editing);
    selectAcrossGapAndPicture(wrapper);

    press(surface(wrapper), "Backspace");
    await nextTick();

    const edited = editing.workspaceDocument.value!;
    expect(edited.items[0]!.body).toEqual([
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "A " },
          { kind: "gap", gap_id: "gap_001" },
          { kind: "text", marks: [], text: " B D" },
        ],
      },
    ]);
    expect(edited.items[0]!.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
    expect(edited.assets).toEqual([]);
    expectServerValid(edited);
    expect(surface(wrapper).querySelector("[data-asset-id]")).toBeNull();

    // The save payload obeys the same rules.
    expect(await editing.save()).toBe(true);
    const sent = api.saveExamWorkspaceDocument.mock.calls[0]![1].document as NativeExamDocument;
    expectServerValid(sent);
    expect(sent.assets).toEqual([]);

    await editing.history.undo();
    await flushPromises();
    const restored = editing.workspaceDocument.value!;
    expect(restored.items[0]).toEqual(original.items[0]);
    expect(restored.assets).toEqual(original.assets);
    expectServerValid(restored);
    // The editor shows the restored text, gap and picture.
    expect(surface(wrapper).querySelector('[data-gap-id="gap_002"]')).not.toBeNull();
    expect(surface(wrapper).querySelector('[data-asset-id="asset_001"]')).not.toBeNull();
    wrapper.unmount();
  });

  it("Ctrl+Z in the question text runs the workspace Ångra and restores the records", async () => {
    const original = baseline();
    const { editing } = await openEditing(api, original);
    const wrapper = await mountQuestionText(editing);
    selectAcrossGapAndPicture(wrapper);
    press(surface(wrapper), "Backspace");
    await nextTick();
    expect(editing.workspaceDocument.value!.assets).toEqual([]);

    const event = press(surface(wrapper), "z", { ctrlKey: true });
    await vi.waitFor(() => expect(editing.workspaceDocument.value!.assets).toEqual(original.assets));

    expect(event.defaultPrevented).toBe(true);
    expect(editing.workspaceDocument.value!.items[0]).toEqual(original.items[0]);
    wrapper.unmount();
  });

  it("keeps an asset another item, the exam instruction or a part instruction still references", async () => {
    for (const shared of ["item", "instructions", "parent"] as const) {
      stopScopes();
      const start = baseline(
        { assets: [asset("asset_001")] },
        shared === "item" ? pictureOnly("asset_001") : undefined,
      );
      if (shared === "instructions") {
        start.instructions = pictureOnly("asset_001");
      }
      if (shared === "parent") {
        start.parents = [
          {
            parent_id: "parent_001",
            instruction: pictureOnly("asset_001"),
            item_ids: ["item_002"],
          },
        ] as unknown as NativeExamDocument["parents"];
      }
      const { editing } = await openEditing(api, start);
      const wrapper = await mountQuestionText(editing);
      selectAcrossGapAndPicture(wrapper);

      press(surface(wrapper), "Backspace");
      await nextTick();

      expect(editing.workspaceDocument.value!.items[0]!.body[0]!.segments.some((s) => s.kind === "asset")).toBe(false);
      expect(editing.workspaceDocument.value!.assets.map((entry) => entry.asset_id)).toEqual(["asset_001"]);
      wrapper.unmount();
    }
  });

  it("saves a gap_fill question with no gap after its last gap is deleted", async () => {
    const start = baseline();
    start.items[0] = onlyGapItem(start.items[0]!);
    start.assets = [];
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
    const sent = api.saveExamWorkspaceDocument.mock.calls[0]![1].document as NativeExamDocument;
    expect(sent.items[0]!.gaps).toEqual([]);
    expectServerValid(sent);
    wrapper.unmount();
  });

  it("saves the empty body when the whole text, only gap included, is deleted", async () => {
    const start = baseline();
    start.items[0] = onlyGapItem(start.items[0]!);
    start.assets = [];
    const { editing } = await openEditing(api, start);
    const wrapper = await mountQuestionText(editing);
    tiptap(wrapper).commands.selectAll();

    press(surface(wrapper), "Backspace");
    await nextTick();

    const edited = editing.workspaceDocument.value!.items[0]!;
    expect(edited.body).toEqual([]);
    expect(edited.gaps).toEqual([]);
    expect(await editing.save()).toBe(true);
    expectServerValid(api.saveExamWorkspaceDocument.mock.calls[0]![1].document as NativeExamDocument);
    wrapper.unmount();
  });

  it("shows the only gap as text, leaving a question with no gap", async () => {
    const start = baseline();
    start.items[0] = onlyGapItem(start.items[0]!);
    start.assets = [];
    const { editing } = await openEditing(api, start);

    editing.showItemGapAsText("item_001", "gap_001");

    const item = editing.workspaceDocument.value!.items[0]!;
    expect(item.gaps).toEqual([]);
    expect(item.body[0]!.segments.map((segment) => (segment.kind === "text" ? segment.text : segment.kind))).toEqual([
      "Svar: ",
      "100",
    ]);
    expectServerValid(editing.workspaceDocument.value!);
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
