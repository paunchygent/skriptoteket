/**
 * Exam workspace asset reference counts (TASK-SKRIPT-39-10-04, repair R3).
 *
 * Expected behavior:
 *   `examWorkspaceAssetReferenceCounts` counts every picture reference the
 *   existing `examWorkspaceReferencedAssetIds` walk visits: an item body, an
 *   item retry source, the exam instruction, and each part instruction.
 *   `examWorkspaceReferencedAssetIds` is that walk's id set, reimplemented
 *   from the counts.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import {
  examWorkspaceAssetReferenceCounts,
  examWorkspaceReferencedAssetIds,
  withReferencedAssetsOnly,
} from "./examWorkspaceStructure";

function paragraph(assetId: string): NativeExamBodyParagraph {
  return { heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] };
}

function question(itemId: string, assetIds: string[]): NativeExamItem {
  return { ...newTeacherItem(itemId, 1, "free_text"), body: assetIds.map(paragraph) };
}

function part(parentId: string, assetIds: string[]): NativeExamParent {
  return { instruction: assetIds.map(paragraph), item_ids: [], parent_id: parentId, place: 0 };
}

function documentOf(options: {
  items?: NativeExamItem[];
  instructions?: NativeExamBodyParagraph[];
  parents?: NativeExamParent[];
}): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: options.instructions ?? [],
    items: options.items ?? [],
    origin: { kind: "created" },
    parents: options.parents ?? [],
    revision: 1,
    schema_version: "native_exam_document_v11",
    title: "Prov",
  };
}

describe("examWorkspaceAssetReferenceCounts", () => {
  it("counts a picture used twice, once, and not at all", () => {
    const document = documentOf({
      items: [question("item_001", ["asset_twice", "asset_twice"])],
      instructions: [paragraph("asset_once")],
    });

    const counts = examWorkspaceAssetReferenceCounts(document);

    expect(counts.get("asset_twice")).toBe(2);
    expect(counts.get("asset_once")).toBe(1);
    expect(counts.has("asset_missing")).toBe(false);
  });

  it("agrees with the referenced id set the pruning keeps", () => {
    const document = documentOf({
      items: [question("item_001", ["asset_seen"])],
      instructions: [paragraph("asset_seen")],
      parents: [part("parent_001", ["asset_seen"])],
    });

    expect(examWorkspaceReferencedAssetIds(document)).toEqual(
      new Set(examWorkspaceAssetReferenceCounts(document).keys()),
    );
    expect(withReferencedAssetsOnly({ ...document, assets: [] }).assets).toEqual([]);
  });
});
