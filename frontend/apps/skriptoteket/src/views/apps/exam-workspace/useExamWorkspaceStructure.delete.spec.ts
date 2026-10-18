/**
 * Deleting a standalone question keeps the native document valid.
 *
 * Expected behavior:
 *   The last question cannot be deleted (refused inline, no edit, no toast);
 *   content tags stop citing a deleted question; only pictures that a
 *   surviving question, retry source, instruction or deluppgift still
 *   references stay. The accepted deletion is one structural edit.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamAsset, NativeExamBodyParagraph, NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

vi.mock("../../../api/examWorkspace", () => ({}));

function asset(assetId: string): NativeExamAsset {
  return { asset_id: assetId, byte_length: 1, media_type: "image/png", sha256: assetId };
}

function picture(assetId: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

function question(sequence: number, assetIds: string[] = []): NativeExamItem {
  const item = newTeacherItem(`item_${String(sequence).padStart(3, "0")}`, sequence, "free_text");
  return { ...item, body: assetIds.flatMap(picture) };
}

function withRetrySource(item: NativeExamItem, assetId: string): NativeExamItem {
  const chunk = {
    anchor: "a",
    images: [{ asset_id: assetId, marked_offset: 0, offset: 0 }],
    kind: "paragraph",
    marked_text: "",
    missing_images: [],
    paragraphs: [],
    runs: [],
  };
  return {
    ...item,
    retry_source: {
      chunks: [],
      context_chunks: [chunk],
      owned_context_anchors: [],
      key_chunks: [],
      label_kind: "free_text",
    },
  } as unknown as NativeExamItem;
}

function documentOf(overrides: Partial<NativeExamDocument>): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items: [question(1), question(2)],
    origin: { kind: "docx_import" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v7",
    title: "Prov",
    ...overrides,
  } as NativeExamDocument;
}

function setup(initial: NativeExamDocument) {
  const workspaceDocument = ref<NativeExamDocument | null>(initial);
  const selectedItemId = ref<string | null>(null);
  const editDocument = vi.fn((edit: (document: NativeExamDocument) => NativeExamDocument) => {
    workspaceDocument.value = edit(workspaceDocument.value!);
    return true;
  });
  const structure = effectScope().run(() =>
    useExamWorkspaceStructure({
      applyCommandResponse: vi.fn(),
      editDocument,
      flush: vi.fn(async () => true),
      historyCursor: ref("cursor"),
      isBusy: () => false,
      lineageId: () => "lineage-1",
      onConflict: vi.fn(async () => undefined),
      replaceCopy: (run) => run(),
      savedRevision: () => 1,
      selectItem: vi.fn(),
      selectedItemId,
      workspaceDocument,
    }),
  )!;
  return { editDocument, structure, workspaceDocument };
}

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("deleting a standalone question", () => {
  it("refuses to delete the only question: no edit, inline notice, no toast", () => {
    const only = documentOf({ items: [question(1)] });
    const { editDocument, structure, workspaceDocument } = setup(only);

    structure.deleteItem("item_001");

    expect(editDocument).not.toHaveBeenCalled();
    expect(workspaceDocument.value).toStrictEqual(only);
    expect(structure.deleteNotice.value).toEqual({ kind: "refused", text: "Provet måste ha minst en fråga." });
    expect(useToastStore().toasts).toEqual([]);
  });

  it("clears an earlier refusal when a later delete is accepted", () => {
    const { structure, workspaceDocument } = setup(documentOf({ items: [question(1), question(2)] }));
    structure.deleteItem("item_001");
    expect(structure.deleteNotice.value).toBeNull();
    structure.deleteItem("item_002");
    expect(structure.deleteNotice.value?.kind).toBe("refused");
    expect(workspaceDocument.value!.items.map((item) => item.item_id)).toEqual(["item_002"]);
  });

  it("removes citations of the deleted question and keeps the others", () => {
    const { editDocument, structure, workspaceDocument } = setup(
      documentOf({
        header: {
          tags: [
            { id: "tag_1", origin: "teacher", question_ids: ["item_001", "item_002"], text: "Båda" },
            { id: "tag_2", origin: "suggested", question_ids: ["item_001"], text: "Bara första" },
          ],
        },
      } as Partial<NativeExamDocument>),
    );

    structure.deleteItem("item_001");

    expect(editDocument).toHaveBeenCalledTimes(1);
    expect(workspaceDocument.value!.header.tags.map((tag) => [tag.id, tag.question_ids])).toEqual([
      ["tag_1", ["item_002"]],
      ["tag_2", []],
    ]);
  });

  it("drops a picture only the deleted question used", () => {
    const { structure, workspaceDocument } = setup(
      documentOf({
        assets: [asset("asset_a"), asset("asset_b")],
        items: [question(1, ["asset_a"]), question(2, ["asset_b"])],
      }),
    );

    structure.deleteItem("item_001");

    expect(workspaceDocument.value!.assets.map((entry) => entry.asset_id)).toEqual(["asset_b"]);
  });

  it.each([
    ["another question", { items: [question(1, ["asset_a"]), question(2, ["asset_a"])] }],
    ["a retry source", { items: [question(1, ["asset_a"]), withRetrySource(question(2), "asset_a")] }],
    ["the document instructions", { instructions: picture("asset_a") }],
    [
      "a parent instruction",
      {
        items: [question(1, ["asset_a"]), question(2), question(3)],
        parents: [{ instruction: picture("asset_a"), item_ids: ["item_003"], parent_id: "parent_001", place: 2 }],
      },
    ],
  ] as [string, Partial<NativeExamDocument>][])("keeps a picture still used by %s", (_label, overrides) => {
    const { structure, workspaceDocument } = setup(documentOf({ assets: [asset("asset_a")], ...overrides }));

    structure.deleteItem("item_001");

    expect(workspaceDocument.value!.assets.map((entry) => entry.asset_id)).toEqual(["asset_a"]);
  });
});
