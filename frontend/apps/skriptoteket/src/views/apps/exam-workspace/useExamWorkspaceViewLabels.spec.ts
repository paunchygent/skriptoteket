/**
 * Exam workspace view labels.
 *
 * Expected behavior:
 *   The instruction preview is the instruction text, or null for an
 *   instruction that prints nothing. The printed total is null without a
 *   document and the computed difference with one. The course label follows
 *   the document's course. Saved exports format through the shared timestamp
 *   helper per export target. The zero-points flag is true while any question
 *   is worth 0 points.
 */

import { describe, expect, it } from "vitest";
import { computed, ref } from "vue";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspaceExports";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import { buildDocument } from "../ExamWorkspaceSlice.specSupport";
import { examWorkspaceSavedAt } from "./examWorkspaceFormat";
import { examWorkspaceExamPrintedDifference } from "./examWorkspaceTotals";
import { useExamWorkspaceViewLabels } from "./useExamWorkspaceViewLabels";

function arrange(params: {
  document?: NativeExamDocument | null;
  savedExports?: Partial<Record<ExamWorkspaceExportTarget, string>>;
  items?: NativeExamItem[];
} = {}) {
  const workspaceDocument = ref<NativeExamDocument | null>(params.document ?? null);
  const savedExports = ref<Partial<Record<ExamWorkspaceExportTarget, string>>>(params.savedExports ?? {});
  const itemList = params.items ?? [];
  const labels = useExamWorkspaceViewLabels({
    items: computed(() => itemList),
    savedExports,
    workspaceDocument,
  });
  return { labels };
}

describe("useExamWorkspaceViewLabels", () => {
  it("previews the instruction text", () => {
    const { labels } = arrange({ document: buildDocument() });

    expect(labels.examInstructionsPreview.value).toBe("Besvara alla frågor.");
  });

  it("previews null for an instruction that prints nothing", () => {
    const { labels } = arrange({ document: { ...buildDocument(), instructions: [] } });

    expect(labels.examInstructionsPreview.value).toBeNull();
  });

  it("reports no printed total without a document and the computed difference with one", () => {
    expect(arrange().labels.examPrintedTotal.value).toBeNull();

    const document = buildDocument();
    const { labels } = arrange({ document });
    expect(labels.examPrintedTotal.value).toBe(examWorkspaceExamPrintedDifference(document));
  });

  it("reports no course label for a document without a course", () => {
    const { labels } = arrange({ document: buildDocument() });

    expect(labels.courseLabel.value).toBeNull();
  });

  it("formats saved exports through the shared timestamp helper", () => {
    const iso = "2026-10-09T08:00:00Z";
    const { labels } = arrange({ savedExports: { pdf: iso } });

    expect(labels.formattedSavedExports.value).toEqual({ pdf: examWorkspaceSavedAt(iso) });
    expect(arrange().labels.formattedSavedExports.value).toEqual({});
  });

  it("flags an exam with a zero-point question", () => {
    expect(arrange({ items: [buildFreeTextItem(1)] }).labels.zeroPoints.value).toBe(false);
    expect(
      arrange({ items: [{ ...buildFreeTextItem(1), points: 0 }] }).labels.zeroPoints.value,
    ).toBe(true);
  });
});
