/**
 * Exam workspace export drawer checklist labels.
 *
 * Expected behavior:
 *   Each checklist row names its question with the question list's label for
 *   the entry's item id ("Fråga 2", "Fråga 1b"), never the flat sequence the
 *   server used to send and never "Fråga NaN". A row whose item id has no
 *   list label shows the bare question text.
 */

import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import type {
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import type { ExamWorkspaceExportChecklistEntry } from "../../../api/examWorkspaceExports";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import ExamWorkspaceExportDrawer from "./ExamWorkspaceExportDrawer.vue";
import { examWorkspaceQuestionLabels } from "./examWorkspaceListEntries";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

function examDocument(items: NativeExamItem[]): NativeExamDocument {
  const children = items.slice(0, 3);
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items,
    origin: { kind: "created" },
    parents: [
      {
        instruction: [],
        item_ids: children.map((child) => child.item_id),
        parent_id: "parent_001",
        place: 0,
      },
    ],
    revision: 1,
    schema_version: "native_exam_document_v8",
    title: "Prov",
  };
}

function criteriaEntry(itemId: string, questionText: string): ExamWorkspaceExportChecklistEntry {
  return {
    criteria: [{ points: 2, text: "Rätt begrepp." }],
    item_id: itemId,
    kind: "free_text_criteria",
    points: 2,
    question_text: questionText,
  };
}

function mountDrawer(
  checklist: ExamWorkspaceExportChecklistEntry[],
  questionLabel: (itemId: string) => string | null,
) {
  return mount(ExamWorkspaceExportDrawer, {
    props: {
      blockers: [],
      busy: false,
      checklist,
      exportingTarget: null,
      notice: null,
      questionLabel,
      result: null,
      savedExports: {},
      suggestBusy: false,
      zeroPoints: false,
    },
    global: {
      plugins: [createPinia(), examWorkspaceProvidersPlugin()],
    },
  });
}

function rowTexts(wrapper: ReturnType<typeof mountDrawer>): string[] {
  return wrapper
    .get('[data-test="exam-workspace-export-checklist"]')
    .findAll("li b")
    .map((heading) => heading.text());
}

describe("ExamWorkspaceExportDrawer checklist labels", () => {
  it("names the row after a part of children by its list label, not its sequence", () => {
    const items = [1, 2, 3, 4].map((sequence) => buildFreeTextItem(sequence));
    const document = examDocument(items);
    const labels = examWorkspaceQuestionLabels(document);
    const wrapper = mountDrawer(
      [criteriaEntry("item_004", "Resonera om satsdelar.")],
      (itemId) => labels.get(itemId) ?? null,
    );

    const rows = rowTexts(wrapper);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toContain("Fråga 2: Resonera om satsdelar.");
    expect(rows[0]).not.toContain("Fråga 4");
    expect(rows[0]).not.toContain("NaN");
  });

  it("names a child row with its letter and never prints a sequence number", () => {
    const items = [1, 2, 3, 4].map((sequence) => buildFreeTextItem(sequence));
    const document = examDocument(items);
    const labels = examWorkspaceQuestionLabels(document);
    const wrapper = mountDrawer(
      [
        criteriaEntry("item_002", "Förklara fotosyntesen."),
        criteriaEntry("item_004", "Resonera om satsdelar."),
      ],
      (itemId) => labels.get(itemId) ?? null,
    );

    const rows = rowTexts(wrapper);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toContain("Fråga 1b: Förklara fotosyntesen.");
    expect(rows[1]).toContain("Fråga 2: Resonera om satsdelar.");
    expect(rows.join(" ")).not.toContain("NaN");
  });

  it("shows the bare question text when the item id has no list label", () => {
    const wrapper = mountDrawer(
      [criteriaEntry("item_009", "Borttagen fråga.")],
      () => null,
    );

    const rows = rowTexts(wrapper);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toBe("Borttagen fråga.");
    expect(rows[0]).not.toContain("Fråga");
  });
});
