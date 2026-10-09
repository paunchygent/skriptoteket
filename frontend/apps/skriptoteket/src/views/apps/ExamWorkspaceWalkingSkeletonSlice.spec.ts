/**
 * Exam workspace walking-skeleton slice behavior.
 *
 * Slice purpose:
 *   Lock the end-to-end teacher loop: import a .docx exam, review extracted
 *   items, edit the selected item, add a new question, save a versioned
 *   revision, recover from a stale-save conflict, and reload the latest saved
 *   version.
 *
 * Expected behavior:
 *   Saving bumps the document revision client-side and sends the previous
 *   revision as `expected_revision`. A 409 shows Swedish conflict handling and
 *   reloads the latest saved version. Teacher answer-key edits become
 *   `teacher_authored`; marking a machine proposal as reviewed becomes
 *   `reviewed_advisory`.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
  NativeExamItem,
} from "../../api/examWorkspace";
import { mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../api/examWorkspace", () => ({
  getExamWorkspaceDocument: apiMocks.getExamWorkspaceDocument,
  importExamWorkspaceDocument: apiMocks.importExamWorkspaceDocument,
  saveExamWorkspaceDocument: apiMocks.saveExamWorkspaceDocument,
}));

function buildFreeTextItem(sequence: number): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: [], origin: "not_applicable" },
    body: [
      { segments: [{ kind: "text", text: `Fråga ${sequence}: beskriv med egna ord.` }] },
    ],
    choices: [],
    gaps: [],
    item_id: `item_${String(sequence).padStart(3, "0")}`,
    kind: "free_text",
    points: 2,
    review: {
      confidence: 0.9,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence,
    source_anchor: null,
    title: `Fråga ${sequence}`,
  };
}

function buildDocument(): NativeExamDocument {
  const items: NativeExamItem[] = [
    buildFreeTextItem(1),
    {
      ...buildFreeTextItem(2),
      answer_key: { correct_choice_ids: ["choice_a"], origin: "source_provided" },
      choices: [
        { choice_id: "choice_a", text: "Avdunstning" },
        { choice_id: "choice_b", text: "Kondensation" },
        { choice_id: "choice_c", text: "Nederbörd" },
      ],
      kind: "single_choice",
      title: "Vattnets kretslopp",
    },
    {
      ...buildFreeTextItem(3),
      answer_key: {
        correct_choice_ids: ["choice_a", "choice_b"],
        origin: "machine_proposed",
      },
      choices: [
        { choice_id: "choice_a", text: "Syre" },
        { choice_id: "choice_b", text: "Kväve" },
        { choice_id: "choice_c", text: "Argon" },
      ],
      kind: "multiple_response",
      review: {
        confidence: 0.4,
        parse_origin: "llm_parsed",
        reasons: ["föreslaget facit behöver godkännas"],
        state: "review_required",
      },
      title: "Luftens gaser",
    },
    {
      ...buildFreeTextItem(4),
      body: [
        {
          segments: [
            { kind: "text", text: "Vatten kokar vid" },
            { gap_id: "gap_001", kind: "gap" },
            { kind: "text", text: "grader." },
          ],
        },
      ],
      gaps: [{ accepted_values: ["100"], gap_id: "gap_001", hint: null }],
      kind: "gap_fill",
      review: {
        confidence: 0.5,
        parse_origin: "llm_parsed",
        reasons: ["luckan behöver godkända svar"],
        state: "review_required",
      },
      title: "Kokpunkt",
    },
    buildFreeTextItem(5),
    buildFreeTextItem(6),
    buildFreeTextItem(7),
    buildFreeTextItem(8),
  ];

  return {
    assets: [],
    document_id: "doc-1",
    instructions: ["Besvara alla frågor."],
    items,
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "abc123",
    },
    revision: 1,
    schema_version: "native_exam_document_v1",
    title: "NO-prov HT25",
  };
}

function buildResponse(params: {
  title?: string;
  version: number;
}): ExamWorkspaceDocumentResponse {
  const document = buildDocument();
  return {
    document: {
      ...document,
      revision: params.version,
      title: params.title ?? document.title,
    },
    notes: [],
    summary: {
      lineage_id: "lineage-1",
      name: params.title ?? document.title,
      saved_at: "2026-10-09T08:00:00Z",
      vault_file_id: "file-1",
      version: params.version,
    },
  };
}

function mountView() {
  return mountWithContext(ExamWorkspaceView);
}

type ViewWrapper = ReturnType<typeof mountView>;

async function importFixtureDocument(wrapper: ViewWrapper) {
  const input = wrapper.find<HTMLInputElement>(
    '[data-test="exam-workspace-source-file-input"]',
  );
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [
      new File(["prov"], "NO_Prov_HT25.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    ],
  });
  await input.trigger("change");
  await flushPromises();
}

async function selectItemRow(wrapper: ViewWrapper, itemId: string) {
  await wrapper.find(`[data-test="exam-workspace-item-row-${itemId}"]`).trigger("click");
}

async function saveDocument(wrapper: ViewWrapper) {
  await wrapper.find('[data-test="exam-workspace-save"]').trigger("click");
  await flushPromises();
}

function lastSavedDocument(): NativeExamDocument {
  const calls = apiMocks.saveExamWorkspaceDocument.mock.calls;
  const [, params] = calls[calls.length - 1] as [
    string,
    { document: NativeExamDocument; expectedRevision: number },
  ];
  return params.document;
}

beforeEach(() => {
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.importExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 1 }));
});

describe("ExamWorkspaceView walking skeleton slice", () => {
  it("shows the extracted items with Swedish type labels and review status after import", async () => {
    const wrapper = mountView();

    await importFixtureDocument(wrapper);

    expect(wrapper.findAll('[data-test^="exam-workspace-item-row-"]')).toHaveLength(8);
    expect(wrapper.text()).toContain("Fritext");
    expect(wrapper.text()).toContain("Flerval: ett val");
    expect(wrapper.text()).toContain("Flerval: flera val");
    expect(wrapper.text()).toContain("Lucktext");
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_003"]').text(),
    ).toContain("Behöver granskas");
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_001"]').text(),
    ).toContain("Granskad");
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
  });

  it("marks the workspace as unsaved when the selected item title is edited", async () => {
    const wrapper = mountView();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-title-input"]')
      .setValue("Helt ny rubrik");

    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').text()).toBe("Osparat");
    expect(wrapper.find('[data-test="exam-workspace-item-row-item_002"]').text()).toContain(
      "Helt ny rubrik",
    );
  });

  it("adds a new teacher-created free-text question with the next free item id", async () => {
    const wrapper = mountView();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-add-item"]').trigger("click");

    expect(wrapper.findAll('[data-test^="exam-workspace-item-row-"]')).toHaveLength(9);
    const newRow = wrapper.find('[data-test="exam-workspace-item-row-item_009"]');
    expect(newRow.exists()).toBe(true);
    expect(newRow.text()).toContain("Fritext");
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').text()).toContain(
      "Fråga 9",
    );
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(true);
  });

  it("saves with the bumped client-side revision and the previous expected revision", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const wrapper = mountView();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-title-input"]')
      .setValue("Helt ny rubrik");
    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const [lineageId, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0] as [
      string,
      { document: NativeExamDocument; expectedRevision: number },
    ];
    expect(lineageId).toBe("lineage-1");
    expect(params.expectedRevision).toBe(1);
    expect(params.document.revision).toBe(2);
    const savedItem = params.document.items.find((item) => item.item_id === "item_002");
    expect(savedItem?.title).toBe("Helt ny rubrik");
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Version 2");
  });

  it("marks a machine-proposed answer key as reviewed_advisory when the item is marked reviewed", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const wrapper = mountView();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    await wrapper.find('[data-test="exam-workspace-mark-reviewed"]').trigger("click");

    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_003"]').text(),
    ).toContain("Granskad");

    await saveDocument(wrapper);

    const savedItem = lastSavedDocument().items.find(
      (item) => item.item_id === "item_003",
    );
    expect(savedItem?.review.state).toBe("review_complete");
    expect(savedItem?.answer_key.origin).toBe("reviewed_advisory");
  });

  it("stores teacher answer-key edits as teacher_authored for choices and gaps", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const wrapper = mountView();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-choice-correct-choice_b"]')
      .setValue(true);

    await selectItemRow(wrapper, "item_004");
    const gapInput = wrapper.find('[data-test="exam-workspace-gap-values-gap_001"]');
    await gapInput.setValue("hundra, 100");
    await gapInput.trigger("change");

    await saveDocument(wrapper);

    const savedDocument = lastSavedDocument();
    const choiceItem = savedDocument.items.find((item) => item.item_id === "item_002");
    expect(choiceItem?.answer_key).toEqual({
      correct_choice_ids: ["choice_b"],
      origin: "teacher_authored",
    });
    const gapItem = savedDocument.items.find((item) => item.item_id === "item_004");
    expect(gapItem?.answer_key.origin).toBe("teacher_authored");
    expect(gapItem?.gaps[0]?.accepted_values).toEqual(["hundra", "100"]);
  });

  it("maps a stale save to Swedish conflict handling and reloads the latest version", async () => {
    apiMocks.saveExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "CONFLICT_STALE_REVISION",
        message: "Stale revision",
        status: 409,
      }),
    );
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(
      buildResponse({ title: "Serverversion av provet", version: 2 }),
    );
    const wrapper = mountView();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-title-input"]')
      .setValue("Helt ny rubrik");
    await saveDocument(wrapper);

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-conflict-notice"]').text()).toContain(
      "ändrades någon annanstans",
    );
    expect(wrapper.text()).toContain("Serverversion av provet");
    expect(wrapper.text()).toContain("Version 2");
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
  });

  it("reloads the latest saved version on request", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(
      buildResponse({ title: "Uppdaterat prov", version: 1 }),
    );
    const wrapper = mountView();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-reload"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1");
    expect(wrapper.text()).toContain("Uppdaterat prov");
  });
});
