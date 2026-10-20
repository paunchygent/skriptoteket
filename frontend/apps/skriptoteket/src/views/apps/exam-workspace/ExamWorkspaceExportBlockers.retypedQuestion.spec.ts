/**
 * Export blockers for a retyped unconverted question (TASK-SKRIPT-39-05-15 D3-D4).
 *
 * Expected behavior:
 *   The new reason "unreviewed_retyped_question" renders the exact copy line
 *   with the existing "Markera som granskad" fix that focuses the existing
 *   review button; once the question is marked reviewed the reason is gone.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { buildDocument } from "../ExamWorkspaceSlice.specSupport";
import {
  EXAM_WORKSPACE_BLOCKER_FIX_LABELS,
  examWorkspaceBlockerEntries,
} from "./examWorkspaceBlockers";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import ExamWorkspaceExportBlockers from "./ExamWorkspaceExportBlockers.vue";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import type { ExamWorkspaceReadinessReason } from "./examWorkspaceItemReadiness";
import { examWorkspaceListEntries } from "./examWorkspaceListEntries";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { EXAM_WORKSPACE_EXPORT_BLOCKER_COPY } from "./useExamWorkspaceExports";

const COPY = "Frågan har fått en ny typ men är inte granskad. Kontrollera den och markera den som granskad.";

function retypedItem(itemId: string, sequence: number): NativeExamItem {
  return {
    ...gapItem("teacher_authored", [["gap_001", ["Paris"]]], null),
    item_id: itemId,
    sequence,
    review: { confidence: null, parse_origin: "teacher_created", reasons: [], state: "review_required" },
  };
}

function rows(items: NativeExamItem[]): ExamWorkspaceBlockerEntry[] {
  const document = { ...buildDocument(), items, parents: [] };
  const readiness: Record<string, ExamWorkspaceReadinessReason[]> = Object.fromEntries(
    items.map((item) => [item.item_id, examWorkspaceItemReadiness(item)]),
  );
  const entries = examWorkspaceListEntries(document, readiness, new Set());
  return examWorkspaceBlockerEntries(entries, items, readiness, {});
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
});

describe("examWorkspaceBlockerEntries for a retyped unconverted question", () => {
  it("names the exact copy line with the review fix on the review button", () => {
    expect(EXAM_WORKSPACE_EXPORT_BLOCKER_COPY.unreviewed_retyped_question).toBe(COPY);

    expect(rows([retypedItem("item_001", 1)])).toEqual([
      {
        fix: "review",
        focus: '[data-test="exam-workspace-review"]',
        itemId: "item_001",
        label: "1",
        problem: "inte granskad",
        reason: "unreviewed_retyped_question",
      },
    ]);
  });

  it("renders the panel row with the fix that emits on click", async () => {
    const [blocker] = rows([retypedItem("item_001", 1)]);
    if (blocker === undefined) throw new Error("expected one blocker row");
    const wrapper = mount(ExamWorkspaceExportBlockers, {
      global: { plugins: [pinia, examWorkspaceProvidersPlugin()] },
      props: { blockers: [blocker], fixDisabled: false, suggestBusy: false, testId: "exam-workspace-export-blockers" },
    });

    expect(wrapper.get('[data-test="exam-workspace-blocker-item_001"]').text()).toContain("Fråga 1: inte granskad");
    const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
    expect(fix.text()).toBe(EXAM_WORKSPACE_BLOCKER_FIX_LABELS.review);
    expect(fix.text()).toBe("Markera som granskad");

    await fix.trigger("click");
    expect(wrapper.emitted("fix")).toEqual([[blocker]]);
  });

  it("drops the reason once the retyped question is marked reviewed", () => {
    const item = retypedItem("item_001", 1);
    const reviewed: NativeExamItem = { ...item, review: { ...item.review, state: "review_complete" } };

    expect(examWorkspaceItemReadiness(reviewed)).toEqual([]);
    expect(rows([reviewed])).toEqual([]);
  });
});
