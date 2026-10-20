/**
 * Question list row for a retyped unconverted question (TASK-SKRIPT-39-05-15 D6).
 *
 * Expected behavior:
 *   A review_required teacher_created question takes the short problem label
 *   "inte granskad" on its list row; a reviewed one names no problem.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import type { ExamWorkspaceReadinessReason } from "./examWorkspaceItemReadiness";
import { examWorkspaceListEntries } from "./examWorkspaceListEntries";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";

function retypedItem(state: NativeExamItem["review"]["state"]): NativeExamItem {
  return {
    ...gapItem("teacher_authored", [["gap_001", ["Paris"]]], null),
    item_id: "item_001",
    sequence: 1,
    review: { confidence: null, parse_origin: "teacher_created", reasons: [], state },
  };
}

function documentWith(item: NativeExamItem): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items: [item],
    origin: { kind: "created" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v10",
    title: "Prov",
  };
}

describe("examWorkspaceListEntries for a retyped unconverted question", () => {
  it("names the row's problem inte granskad while review is required", () => {
    const item = retypedItem("review_required");
    const document = documentWith(item);
    const readiness: Record<string, ExamWorkspaceReadinessReason[]> = {
      [item.item_id]: examWorkspaceItemReadiness(item),
    };

    const entries = examWorkspaceListEntries(document, readiness, new Set());

    expect(entries).toMatchObject([{ id: "item_001", kind: "item", problem: "inte granskad" }]);
  });

  it("names no problem once the retyped question is marked reviewed", () => {
    const item = retypedItem("review_complete");
    const document = documentWith(item);
    const readiness: Record<string, ExamWorkspaceReadinessReason[]> = {
      [item.item_id]: examWorkspaceItemReadiness(item),
    };

    const entries = examWorkspaceListEntries(document, readiness, new Set());

    expect(entries).toMatchObject([{ id: "item_001", kind: "item", problem: null }]);
  });
});
