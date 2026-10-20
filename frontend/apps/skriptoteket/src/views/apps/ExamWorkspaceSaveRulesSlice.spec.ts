/**
 * Exam workspace save-rule slice.
 *
 * Expected behavior:
 *   Item states the server refuses to save are flagged at the question and
 *   refused locally with Swedish copy naming the questions: points that are
 *   negative or non-finite, and a choice without text. The field is marked
 *   invalid with an inline hint, the question list and the export blocker
 *   lists carry the reason, and no save request is sent.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  NativeExamChoice,
  NativeExamDocument,
  NativeExamItem,
} from "../../api/examWorkspace";
import { buildFreeTextItem } from "../../test/examWorkspaceFixtures";
import { useToastStore } from "../../stores/toast";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));
const unreadable = vi.hoisted(() => ({ listUnreadableExamWorkspaceDocuments: vi.fn() }));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspaceUnreadableFiles", () => unreadable);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

let mountedView: ViewWrapper | undefined;

/** Attached to the body, because the export menu teleports there. */
async function mountImported() {
  const { wrapper } = await mountExamWorkspace({}, "desktop", document.body);
  mountedView = wrapper;
  await importFixtureDocument(wrapper);
  return wrapper;
}

function bodyElement(testId: string): HTMLElement {
  const element = document.body.querySelector<HTMLElement>(`[data-test="${testId}"]`);
  expect(element, testId).not.toBeNull();
  return element!;
}

async function openExportMenu(wrapper: ViewWrapper) {
  await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
  await flushPromises();
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

beforeEach(() => {
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) {
    mock.mockReset();
  }
  unreadable.listUnreadableExamWorkspaceDocuments.mockReset();
  unreadable.listUnreadableExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  arrangeStepHistory(apiMocks);
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      buildResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
});

afterEach(() => {
  mountedView?.unmount();
  mountedView = undefined;
});

describe("ExamWorkspaceView save rules", () => {
  it("flags negative points at the field and in the drawer, and refuses the save", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("-1");

    expect(points.attributes("aria-invalid")).toBe("true");
    const hint = wrapper.get('[data-test="exam-workspace-points-hint"]');
    expect(hint.text()).toBe("Ange 0 poäng eller mer.");
    expect(points.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(wrapper.get('[data-test="exam-workspace-row-item_002"]').text()).toContain("negativa poäng");

    await openExportMenu(wrapper);
    expect(bodyElement("exam-workspace-blocker-item_002").textContent?.trim()).toBe("Fråga 2: negativa poäng");

    await saveDocument(wrapper);

    // The refused draft never reaches the server; it is held with its reason.
    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toBe("Inte sparat");
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').attributes("title")).toBe(
      "Fråga 2 har negativa poäng. Ange 0 poäng eller mer.",
    );
    expect(vi.mocked(useToastStore().failure)).not.toHaveBeenCalled();
  });

  it("flags negative points in the export drawer's blocker list", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_005");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("-1");
    await openExportMenu(wrapper);
    bodyElement("exam-workspace-export-more").click();
    await flushPromises();

    expect(wrapper.get('[data-test="exam-workspace-blocker-item_005"]').text()).toBe("Fråga 5: negativa poäng");
  });

  it("flags an empty choice text at the field and still saves it", async () => {
    const { wrapper } = await mountExamWorkspace();
    // An emptied choice saves (TASK-SKRIPT-40-04-06 D3) and blocks export instead.
    const response = buildResponse({ conversion: succeededConversion, version: 1 });
    for (const [itemId, choiceId] of [
      ["item_002", "choice_002"],
      ["item_003", "choice_003"],
    ] as const) {
      const choice = response.document.items
        .find((item) => item.item_id === itemId)!
        .choices.find((entry) => entry.choice_id === choiceId)!;
      choice.body = [];
    }
    apiMocks.getExamWorkspaceDocument.mockReset();
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(response);
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    const choice = wrapper.get('[data-test="exam-workspace-choice-text-choice_002"]');

    expect(choice.attributes("aria-invalid")).toBe("true");
    const hint = wrapper.get('[data-test="exam-workspace-choice-text-hint"]');
    expect(hint.text()).toBe("Ett svarsalternativ saknar text.");
    expect(choice.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(
      wrapper.get('[data-test="exam-workspace-choice-text-choice_001"]').attributes("aria-invalid"),
    ).toBeUndefined();
    // A teacher edit makes the copy dirty, so the save button sends it.
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");

    await selectItemRow(wrapper, "item_003");
    await saveDocument(wrapper);

    expect(vi.mocked(useToastStore().failure)).not.toHaveBeenCalled();
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const [, request] = apiMocks.storeExamWorkspaceUndoStep.mock.calls[0]!;
    const saved = request.document.items.find((item: NativeExamItem) => item.item_id === "item_002")!;
    expect(saved.choices.find((entry: NativeExamChoice) => entry.choice_id === "choice_002")!.body).toEqual([]);
  });

  it("accepts zero points at the field and sends the save", async () => {
    const response = buildResponse({ conversion: succeededConversion, version: 1 });
    const document: NativeExamDocument = {
      ...response.document,
      document_id: "00000000-0000-4000-8000-000000000001",
      origin: {
        kind: "docx_import",
        source_filename: "NO_Prov_HT25.docx",
        source_sha256: "a".repeat(64),
        extractor_version: "docx-extractor-1",
      },
      items: [buildFreeTextItem(1), buildFreeTextItem(2)],
    };
    apiMocks.importExamWorkspaceDocument.mockResolvedValue({
      ...succeededConversion, state: "queued", document_revision: null,
    });
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce({
      ...response, document, saved_document: document,
    });
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("0");

    expect(points.attributes("aria-invalid")).toBeUndefined();
    expect(wrapper.find('[data-test="exam-workspace-points-hint"]').exists()).toBe(false);
    await saveDocument(wrapper);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledWith(
      "lineage-1",
      expect.objectContaining({
        document: expect.objectContaining({
          items: expect.arrayContaining([expect.objectContaining({ item_id: "item_002", points: 0 })]),
        }),
      }),
    );
  });

  it("stores again once the refused fields are corrected", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("-1");
    await points.setValue("3");
    await saveDocument(wrapper);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
  });

});
